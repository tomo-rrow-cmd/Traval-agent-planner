"""
TrafficAgent — 闭环路径 + 大交通 + 酒店交通评估
"""

import asyncio
import math
import re
from typing import Any

from app.agents.base import BaseAgent
from app.services.map.amap import AmapService
from app.services.map.geocode import haversine_distance

MEAL_WINDOWS = {"午餐": (11, 14), "晚餐": (17, 21)}


class TrafficAgent(BaseAgent):
    name = "traffic"
    description = "闭环路径 + 大交通 + 酒店评估"

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        dest = input_data.get("destination", "")
        origin = input_data.get("origin", "")
        days = int(input_data.get("days", 1))
        daily_locations = input_data.get("daily_locations", [])
        meal_plan = input_data.get("meal_plan", [])
        hotel_plan = input_data.get("hotel_plan", {})
        preferred = input_data.get("preferred_transport", "transit")
        weather_impact = input_data.get("weather_impact", [])
        start_date = input_data.get("start_date", "")
        end_date = input_data.get("end_date", "")

        amap = AmapService()

        first_day_weather = next(
            (
                impact
                for impact in weather_impact
                if impact.get("day_of_trip") == 1
            ),
            {},
        )
        big_traffic = await _big_traffic(
            origin,
            dest,
            hotel_plan,
            amap,
            days,
            start_date,
            end_date,
            first_day_weather,
        )
        daily_traffic, time_warnings = await _plan_daily(
            amap, daily_locations, meal_plan, hotel_plan, big_traffic, preferred,
            weather_impact, dest)

        total_cost = sum(d["total_cost"] for d in daily_traffic)
        summary = await self._llm_summary(daily_traffic, dest, days, preferred)
        hotel_match = _hotel_match(daily_traffic, hotel_plan)

        return {
            "traffic_plan": daily_traffic,
            "daily_traffic": daily_traffic,
            "big_traffic": big_traffic,
            "total_traffic_cost": round(total_cost, 2),
            "time_warnings": time_warnings,
            "summary": summary,
            "hotel_match": hotel_match,
        }

    async def _llm_summary(self, daily_traffic, dest, days, pref):
        lines = []
        for d in daily_traffic:
            lines.append(f"Day{d['day']}: {d['total_time_min']}min Y{d['total_cost']:.0f}")
        try:
            return await self.call_llm(
                [{"role": "user", "content": f"{dest}{days}天交通总览。{chr(10).join(lines)}。1-2句总结。"}],
                temperature=0.5)
        except Exception:
            return f"{dest}{days}天建议{pref}出行"

    # ---- 酒店交通评估（供 DecisionAgent 调用） ----

    @staticmethod
    async def evaluate_hotels(hotel_plan: dict, daily_plan: list,
                              destination: str) -> list[dict]:
        """
        对每个候选酒店做轻量交通评估，返回排序后的列表。

        不跑完整 TrafficAgent，只计算酒店→每日首景点距离。

        Returns: hotel_plan.recommendations 每项附加 commute_score(0-1)
        """
        recs = hotel_plan.get("recommendations", [])
        if not recs or not daily_plan:
            return recs

        amap = AmapService()
        scored = []

        for r in recs:
            h_lat = r.get("latitude"); h_lng = r.get("longitude")
            if not h_lat or not h_lng:
                r["commute_score"] = 0.5
                r["commute_note"] = "no coordinates"
                scored.append(r)
                continue

            scores = []
            details = []
            for day in daily_plan:
                attrs = day.get("attractions", [])
                if not attrs: continue
                first = attrs[0]
                a_lat = first.get("latitude"); a_lng = first.get("longitude")
                if a_lat and a_lng:
                    dist = haversine_distance(h_lat, h_lng, a_lat, a_lng)
                    try:
                        opts = await _route_options(
                            amap,
                            f"{h_lng},{h_lat}",
                            f"{a_lng},{a_lat}",
                            destination,
                        )
                        sel = _select_route_option(opts, "transit")
                        time_min = sel["time_min"] if sel else int(dist / 20 * 60)
                    except Exception:
                        time_min = int(dist / 20 * 60)
                    s = 1.0 if time_min <= 20 else (0.8 if time_min <= 40 else (0.5 if time_min <= 60 else 0.3))
                    scores.append(s)
                    details.append({"day": day["day"], "to": first["name"][:10],
                                    "distance_km": round(dist, 1), "time_min": time_min, "score": round(s, 2)})

            avg = sum(scores) / len(scores) if scores else 1.0
            r["commute_score"] = round(avg, 2)
            r["commute_details"] = details
            scored.append(r)

        scored.sort(key=lambda x: x.get("commute_score", 0), reverse=True)
        return scored


# ================================================================
#  大交通
# ================================================================

async def _big_traffic(
    origin: str,
    dest: str,
    hotel_plan: dict,
    amap,
    days: int = 1,
    start_date="",
    end_date="",
    first_day_weather=None,
) -> dict:
    from datetime import date as dt, timedelta
    result = {"trains": [], "return_trains": [], "flights": [], "origin_hub": None, "arrival_hub": None,
              "departure_hub": None, "hub_to_hotel": None,
              "recommend_mode": "train", "city_distance_km": 0}
    if not origin or not dest or origin == dest:
        return result

    hub = await _find_hubs(amap, dest)
    origin_hub = await _find_hubs(amap, origin)

    # 先算距离确定推荐交通方式
    dest_airport = hub.get("airport")
    dest_station = hub.get("station")
    origin_airport = origin_hub.get("airport")
    origin_station = origin_hub.get("station")

    # 用机场算距离（机场间距离最有代表性）
    if origin_airport and dest_airport:
        dist = haversine_distance(origin_airport["lat"], origin_airport["lng"],
                                  dest_airport["lat"], dest_airport["lng"])
        result["city_distance_km"] = round(dist, 1)
        result["recommend_mode"] = "flight" if dist > 1000 else "train"
    elif origin_station and dest_station:
        dist = haversine_distance(origin_station["lat"], origin_station["lng"],
                                  dest_station["lat"], dest_station["lng"])
        result["city_distance_km"] = round(dist, 1)
        result["recommend_mode"] = "flight" if dist > 1000 else "train"

    # 按推荐方式选择出发地与目的地枢纽。
    if result["recommend_mode"] == "flight":
        selected_origin_hub = origin_airport or origin_station
        selected_dest_hub = dest_airport or dest_station
    else:
        selected_origin_hub = origin_station or origin_airport
        selected_dest_hub = dest_station or dest_airport
    result["origin_hub"] = selected_origin_hub
    result["arrival_hub"] = selected_dest_hub
    result["departure_hub"] = selected_dest_hub

    # ---- 去程火车票（出发日） ----
    go_date = str(start_date or dt.today() + timedelta(days=1))
    try:
        from app.services.third_party.railway12306 import railway
        trains = railway.query_all_trains(origin, dest, go_date)[:15]
        for train in trains:
            try:
                train["prices"] = railway.query_price(
                    train.get("trainNo", ""),
                    train.get("fromStationNo", ""),
                    train.get("toStationNo", ""),
                    go_date,
                    train.get("seatTypes", ""),
                )
            except Exception:
                train["prices"] = {}
        result["trains"] = trains
    except Exception: pass

    # ---- 返程火车票（返程日） ----
    back_date = str(end_date or dt.today() + timedelta(days=days))
    try:
        from app.services.third_party.railway12306 import railway
        return_trains = railway.query_all_trains(dest, origin, back_date)[:15]
        for train in return_trains:
            try:
                train["prices"] = railway.query_price(
                    train.get("trainNo", ""),
                    train.get("fromStationNo", ""),
                    train.get("toStationNo", ""),
                    back_date,
                    train.get("seatTypes", ""),
                )
            except Exception:
                train["prices"] = {}
        result["return_trains"] = return_trains
    except Exception: pass

    try:
        from app.services.third_party.meituan import meituan
        if meituan.available:
            r = await meituan.query(origin, f"{origin}到{dest}机票")
            if r.get("success"):
                result["flights"] = _parse_flights(r["text"])
    except Exception: pass

    selected_hub = result["arrival_hub"]
    if selected_hub and hotel_plan:
        selected_hotel = _selected_hotel(hotel_plan)
        if selected_hotel.get("latitude") and selected_hotel.get("longitude"):
            r = selected_hotel
            try:
                opts = await _route_options(
                    amap,
                    f"{selected_hub['lng']},{selected_hub['lat']}",
                    f"{r['longitude']},{r['latitude']}",
                    dest,
                )
                weather_adjusted = _apply_weather_speed_factor(
                    opts,
                    first_day_weather,
                )
                sel = _select_route_option(
                    weather_adjusted,
                    "transit",
                    first_day_weather,
                )
                if sel: result["hub_to_hotel"] = {"from": selected_hub["name"], "to": r["name"], **sel}
            except Exception: pass
    return result


# ================================================================
#  市内闭环
# ================================================================

async def _plan_daily(amap, daily_locations, meal_plan, hotel_plan, big_traffic, preferred,
                       weather_impact=None, city=""):
    weather_impact = weather_impact or []
    # Index weather by day_of_trip for O(1) lookup
    weather_by_day = {wi.get("day_of_trip", 0): wi for wi in weather_impact}

    hotel = _selected_hotel(hotel_plan)
    daily_traffic = []; warnings = []

    for day in daily_locations:
        d = day.get("day", 1)
        day_weather = weather_by_day.get(d)
        attrs = _dedupe(day.get("attractions", []))
        meals = _day_meals(meal_plan, d)
        is_first = d == 1
        is_last = d == len(daily_locations)

        stops = []
        if is_first and hotel and big_traffic.get("arrival_hub"):
            h = big_traffic["arrival_hub"]
            stops.append({"name": h["name"], "latitude": h["lat"], "longitude": h["lng"]})
        if hotel.get("name"):
            stops.append({"name": hotel["name"], "latitude": hotel.get("latitude"), "longitude": hotel.get("longitude")})
        stops += _build_stops(attrs, meals)
        if hotel.get("name"):
            stops.append({"name": hotel["name"], "latitude": hotel.get("latitude"), "longitude": hotel.get("longitude")})
        if is_last and hotel and big_traffic.get("departure_hub"):
            h = big_traffic["departure_hub"]
            stops.append({"name": h["name"], "latitude": h["lat"], "longitude": h["lng"]})

        segs, t_time, t_cost, warns = await _route_stops(
            amap,
            stops,
            preferred,
            d,
            day_weather,
            city,
        )
        daily_traffic.append({"day": d, "segments": segs, "total_time_min": t_time, "total_cost": round(t_cost, 2)})
        warnings.extend(warns)

    return daily_traffic, warnings


async def _route_stops(amap, stops, preferred, day, weather=None, city=""):
    weather = weather or {}
    segs = []; total_t = 0; total_c = 0.0; warns = []; clock = 9.0
    for i in range(len(stops) - 1):
        a, b = stops[i], stops[i + 1]
        if _same(a, b): continue
        seg = await _route_between(amap, a, b, preferred, weather, city)
        segs.append(seg); total_t += seg["time_min"]; total_c += seg["cost"]
        arrive = clock + seg["time_min"] / 60
        if b.get("arrive_by") and arrive > b["arrive_by"]:
            warns.append(f"Day{day}: {b['name']}({b.get('meal','')}) 到达{arrive:.0f}:00 > 最晚{b['arrive_by']}:00")
        stay = b.get("duration_h", 0) or (0.75 if b.get("meal") else 0)
        clock = arrive + stay
    return segs, total_t, total_c, warns


def _build_stops(attrs, meals):
    stops = [{"name": a["name"], "latitude": a.get("latitude"), "longitude": a.get("longitude"),
              "duration_h": a.get("duration_hours", 2)} for a in attrs]
    lunch = next((m for m in meals if m.get("meal") == "午餐"), None)
    dinner = next((m for m in meals if m.get("meal") == "晚餐"), None)
    if lunch and len(stops) >= 2:
        stops.insert(len(stops) // 2, {"name": lunch.get("restaurant", ""), "meal": "午餐",
                     "arrive_by": MEAL_WINDOWS["午餐"][1],
                     "latitude": lunch.get("latitude"), "longitude": lunch.get("longitude")})
    if dinner:
        stops.append({"name": dinner.get("restaurant", ""), "meal": "晚餐",
                     "arrive_by": MEAL_WINDOWS["晚餐"][1],
                     "latitude": dinner.get("latitude"), "longitude": dinner.get("longitude")})
    return stops


def _day_meals(meal_plan, day):
    for mp in meal_plan:
        if mp.get("day") == day: return mp.get("meals", [])
    return []


# ================================================================
#  评估与路由
# ================================================================

async def _route_between(amap, a, b, preferred, weather=None, city=""):
    weather = weather or {}
    ac = _coord(a); bc = _coord(b)
    if ac and bc:
        try:
            opts = await _route_options(amap, ac, bc, city)
            weather_adjusted = _apply_weather_speed_factor(opts, weather)
            sel = _select_route_option(weather_adjusted, preferred, weather)
            if sel:
                return {
                    "from": a["name"],
                    "to": b["name"],
                    **sel,
                    "options": _format_route_options(weather_adjusted),
                }
        except Exception: pass
    return _estimate(a, b, preferred, weather)


def _estimate(a, b, mode, weather=None):
    weather = weather or {}
    speed_factor = _speed_factor(weather)

    ac = _coordinates(a)
    bc = _coordinates(b)
    d = haversine_distance(*ac, *bc) if ac and bc else 5.0
    route_type = _route_type(mode)
    sp = {"transit": 25 * speed_factor, "driving": 30 * speed_factor,
          "walking": 5 * speed_factor}
    t = max(1, int(d / sp[route_type] * 60))
    c = d * 3 if route_type == "transit" else d * 1.5
    return {"from": a.get("name",""), "to": b.get("name",""), "distance_km": round(d,1),
            "time_min": t, "cost": round(c,2), "mode": mode + "(est)", "options": []}


def _hotel_match(daily_traffic, hotel_plan):
    hotel = _selected_hotel(hotel_plan)
    if not hotel: return {"score": 0}
    name = hotel.get("name", ""); scores = []; details = []
    for day in daily_traffic:
        segs = day.get("segments", []); s = 1.0; info = {"day": day["day"]}
        if segs:
            f, l = segs[0], segs[-1]
            if f.get("from") == name and f.get("time_min", 0) > 30: s -= 0.15; info["morning"] = f"commute {f['time_min']}min"
            if l.get("to") == name and l.get("time_min", 0) > 30: s -= 0.10; info["evening"] = f"return {l['time_min']}min"
        scores.append(max(0, s)); details.append(info)
    avg = sum(scores) / len(scores) if scores else 1.0
    return {"score": round(avg, 2), "details": details,
            "suggestions": ["consider closer hotel"] if avg < 0.75 else [], "hotel": name}


# ================================================================
#  Helpers
# ================================================================

async def _find_hubs(amap, city) -> dict:
    """查找城市交通枢纽 — 同时返回机场和火车站"""
    hubs = {"airport": None, "station": None}
    try:
        for kw, key in [("国际机场", "airport"), ("火车站", "station")]:
            pois = await amap.search_poi(keywords=kw, city=city, offset=1)
            for p in pois:
                loc = p.get("location", "")
                if loc:
                    parts = loc.split(",")
                    hubs[key] = {"name": p["name"], "lat": float(parts[1]),
                                 "lng": float(parts[0]), "type": key}
                    break
    except Exception:
        pass
    return hubs


async def _route_options(amap, origin, destination, city=""):
    results = await asyncio.gather(
        amap.route_planning(origin, destination, "transit", city=city or None),
        amap.route_planning(origin, destination, "walking"),
        amap.route_planning(origin, destination, "driving"),
        return_exceptions=True,
    )
    opts = []
    for rtype, route in zip(["transit", "walking", "driving"], results):
        if isinstance(route, Exception): continue
        o = _parse_route(rtype, route)
        if o: opts.append(o)
    return opts


def _select_route_option(opts, preferred, weather=None):
    weather = weather or {}

    # 1. Remove walking if not viable
    if not weather.get("walking_viable", True):
        opts = [o for o in opts if o.get("route_type") != "walking"]

    # 2. Weather safety override
    weather_preferred = weather.get("preferred_mode", "")
    if weather_preferred:
        for o in opts:
            if o.get("route_type") == _route_type(weather_preferred):
                return o

    # 3. User preference
    for o in opts:
        if o.get("route_type") == _route_type(preferred): return o
    return opts[0] if opts else None


def _route_type(preferred):
    value = re.sub(r"\s+", "", str(preferred or "")).lower()
    modes = {
        "transit": "transit", "bus": "transit", "subway": "transit",
        "公交": "transit", "地铁": "transit", "公共交通": "transit",
        "walking": "walking", "walk": "walking", "步行": "walking",
        "driving": "driving", "drive": "driving", "taxi": "driving",
        "自驾": "driving", "打车": "driving", "出租车": "driving",
    }
    return modes.get(value, "transit")


def _speed_factor(weather=None):
    try:
        factor = float((weather or {}).get("traffic_speed_factor", 1.0))
    except (TypeError, ValueError):
        return 1.0
    return factor if 0 < factor <= 1 else 1.0


def _apply_weather_speed_factor(opts, weather=None):
    factor = _speed_factor(weather)
    if factor == 1.0:
        return opts
    adjusted = []
    for option in opts:
        updated = dict(option)
        updated["time_min"] = max(
            1,
            math.ceil(float(option.get("time_min", 1)) / factor - 1e-9),
        )
        adjusted.append(updated)
    return adjusted


def _parse_route(rtype, route):
    if rtype == "transit":
        return _parse_transit(route)
    paths = route.get("paths") or [{}]
    if not paths: return None
    p = paths[0]; d = _ai(p.get("distance")); dur = _ai(p.get("duration"))
    km = d/1000; cost = 0.0
    if rtype == "driving":
        cost = _af(route.get("taxi_cost")) or max(13.0, 13 + max(km - 3, 0) * 2.3 + km)
    base = {"route_type": rtype, "mode": "walking" if rtype == "walking" else "driving",
            "distance_km": km, "time_min": max(1, (dur+59)//60), "cost": round(cost, 2)}
    if rtype == "walking":
        base["steps"] = _parse_walking_steps(p)
        base["detail"] = _walking_summary(p, km)
    else:
        base["steps"] = _parse_driving_steps(p)
        base["detail"] = _driving_summary(p)
        base["tolls"] = _af(p.get("tolls", 0))
        base["toll_distance"] = _ai(p.get("toll_distance", 0))
        base["traffic_lights"] = _ai(p.get("traffic_lights", 0))
        base["strategy"] = p.get("strategy", "")
        base["traffic_summary"] = _traffic_summary(p)
        base["road_names"] = _road_names(p)
    return base


def _parse_transit(route):
    """提取公共交通完整信息：所有换乘方案 + 每段详情"""
    all_transits = route.get("transits", [])
    if not all_transits:
        return None

    plans = []
    for tr in all_transits[:3]:  # 最多保留 3 个换乘方案
        segments = []
        for seg in (tr.get("segments") or []):
            walking = seg.get("walking") or {}
            if walking:
                segments.append({
                    "type": "walking",
                    "distance": _ai(walking.get("distance")),
                    "duration": _ai(walking.get("duration")),
                    "steps": _parse_walking_steps(walking),
                })

            buslines = (seg.get("bus") or {}).get("buslines") or []
            if buslines:
                bus = buslines[0]
                raw_type = bus.get("type", "")
                line_name = str(bus.get("name", ""))
                if "地铁" in raw_type or "地铁" in line_name:
                    segment_type = "SUBWAY"
                elif "公交" in raw_type or "巴士" in raw_type:
                    segment_type = "BUS"
                else:
                    segment_type = raw_type or "BUS"
                bus_segment = {
                    "type": segment_type,
                    "line_name": line_name.split("(", 1)[0].strip(),
                    "line_full": bus.get("name", ""),
                    "departure_stop": (bus.get("departure_stop") or {}).get("name", ""),
                    "arrival_stop": (bus.get("arrival_stop") or {}).get("name", ""),
                    "via_stops": _ai(bus.get("via_num", bus.get("via_stops", 0))),
                    "distance": _ai(bus.get("distance")),
                    "duration": _ai(bus.get("duration")),
                    "start_time": bus.get("start_time", "") or bus.get("station_start_time", ""),
                    "end_time": bus.get("end_time", "") or bus.get("station_end_time", ""),
                    "direction": bus.get("direction", ""),
                }
                if isinstance(bus.get("via_stops"), list) and bus["via_stops"]:
                    bus_segment["via_stops"] = len(bus["via_stops"])
                    bus_segment["via_stop_names"] = bus["via_stops"][:5]
                segments.append(bus_segment)

        plan = {
            "cost": _af(tr.get("cost", 0)),
            "duration": _ai(tr.get("duration", 0)),
            "walking_distance": _ai(tr.get("walking_distance", 0)),
            "distance": _ai(tr.get("distance", 0)),
            "segments": segments,
            "night_bus": tr.get("nightflag") == "1",
        }
        plans.append(plan)

    best = plans[0] if plans else {}
    return {
        "route_type": "transit",
        "mode": "transit",
        "distance_km": _ai(best.get("distance", 0)) / 1000,
        "time_min": max(1, (_ai(best.get("duration", 0)) + 59) // 60),
        "cost": _af(best.get("cost", 0)),
        "walking_distance": best.get("walking_distance", 0),
        "plans": plans,                               # 所有换乘方案
        "detail": _transit_detail(best),
        "plan_count": len(plans),
    }


def _transit_detail(plan):
    """公交路线一句话摘要"""
    if not plan:
        return "暂无详情"
    segs = plan.get("segments", [])
    parts = []
    for s in segs:
        if s.get("type") == "walking":
            if s.get("distance"):
                parts.append(f"步行 {s['distance']}m")
            else:
                parts.append(f"步行 {s.get('duration',0)//60}min")
        elif s.get("type") == "SUBWAY":
            route = s.get("line_name", "?")
            if s.get("departure_stop") or s.get("arrival_stop"):
                route += f"({s.get('departure_stop','?')}→{s.get('arrival_stop','?')})"
            parts.append(route)
        elif s.get("type") == "BUS":
            parts.append(f"公交{s.get('line_name','?')}")
    return " -> ".join(parts) if parts else "无详情"


def _parse_walking_steps(path_seg):
    """步行步骤 → 结构化列表"""
    steps = []
    for s in (path_seg.get("steps") or [])[:10]:
        steps.append({
            "instruction": s.get("instruction", ""),
            "distance": _ai(s.get("distance", 0)),
            "duration": _ai(s.get("duration", 0)),
            "action": s.get("action", ""),
            "orientation": s.get("orientation", ""),
            "road": s.get("road", ""),
        })
    return steps


def _walking_summary(path, km):
    steps_count = len(path.get("steps", []))
    return f"步行 {km:.1f}km · {steps_count}步"


def _parse_driving_steps(path):
    """驾车步骤 → 结构化列表"""
    steps = []
    for s in (path.get("steps") or [])[:10]:
        steps.append({
            "instruction": s.get("instruction", ""),
            "distance": _ai(s.get("distance", 0)),
            "duration": _ai(s.get("duration", 0)),
            "action": s.get("action", ""),
            "road_name": _road_names(s),
        })
    return steps


def _driving_summary(path):
    streets = _distinct_streets(path)
    return "途经 " + "、".join(streets[:3]) if streets else "打车/驾车"


def _traffic_summary(path):
    """驾车路况汇总"""
    tmcs = []
    for s in (path.get("steps") or [])[:10]:
        for t in (s.get("tmcs") or []):
            tmcs.append(t.get("status", "未知"))
    if not tmcs:
        return ""
    from collections import Counter
    c = Counter(tmcs)
    return "、".join(f"{v}段{k}" for k, v in c.items())


def _road_names(seg):
    """提取路段中的道路名"""
    road = seg.get("road")
    if isinstance(road, str) and road.strip():
        return [road.strip()]
    if isinstance(road, list):
        roads = [str(name).strip() for name in road if str(name).strip()]
        if roads:
            return list(dict.fromkeys(roads))

    roads = []
    cities = seg.get("cities") or []
    for c in cities[:2]:
        for d in (c.get("districts") or [])[:2]:
            name = d.get("name", "")
            if name:
                roads.append(name)
    return list(dict.fromkeys(roads))


def _distinct_streets(path):
    """驾车路径中所有道路名（去重）"""
    seen = set()
    streets = []
    for s in (path.get("steps") or []):
        for r in _road_names(s):
            if r not in seen:
                seen.add(r)
                streets.append(r)
    return streets[:6]


def _format_route_options(opts):
    labels = {"transit": "公共交通", "walking": "步行", "driving": "打车/驾车"}
    return [
        {
            **opt,
            "mode": labels.get(opt.get("route_type"), opt.get("mode", "")),
        }
        for opt in opts
    ]


def _coordinates(loc):
    try:
        latitude = float(loc.get("latitude"))
        longitude = float(loc.get("longitude"))
    except (TypeError, ValueError):
        return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    if latitude == 0 and longitude == 0:
        return None
    return latitude, longitude


def _coord(loc):
    coords = _coordinates(loc)
    return f"{coords[1]},{coords[0]}" if coords else None


def _selected_hotel(hotel_plan):
    recommendations = hotel_plan.get("recommendations", [])
    selected_hotel = hotel_plan.get("selected_hotel")
    if isinstance(selected_hotel, dict) and selected_hotel.get("name"):
        return selected_hotel
    if not recommendations:
        return {}
    selected = hotel_plan.get("selected")
    selected_name = selected.get("name") if isinstance(selected, dict) else selected
    if selected_name:
        match = next(
            (hotel for hotel in recommendations
             if _norm(hotel.get("name", "")) == _norm(selected_name)),
            None,
        )
        if match:
            return match
    return recommendations[0]


def _dedupe(lst):
    seen, out = set(), []
    for x in lst:
        k = _norm(x.get("name",""));
        if k and k in seen: continue
        seen.add(k); out.append(x)
    return out


def _norm(n): return re.sub(r"\s+", "", str(n).split("(")[0].lower())


def _same(a, b):
    """两站去重：先比名称，再比坐标（仅当双方都有坐标时才用距离判重）"""
    a_name = _norm(a.get("name", ""))
    b_name = _norm(b.get("name", ""))
    if a_name and a_name == b_name:
        return True
    a_coords = _coordinates(a)
    b_coords = _coordinates(b)
    return bool(a_coords and b_coords and haversine_distance(*a_coords, *b_coords) < 0.05)


def _ai(v, d=0): return int(float(str(v or d)))
def _af(v, d=0.0): return float(str(v or d))


def _parse_flights(text):
    import re; flights = []
    for line in text.split("\n"):
        m = re.search(r"([A-Z0-9]{4,6})\s.*?(\d{2}:\d{2}).*?(\d{2}:\d{2})", line.strip())
        if m: flights.append({"flight": m.group(1), "dep": m.group(2), "arr": m.group(3), "source": "meituan"})
    return flights if flights else [{"raw": text[:300], "source": "meituan_raw"}]
