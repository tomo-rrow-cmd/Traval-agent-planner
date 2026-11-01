"""测试 5 阶段管线 — python scripts/test_pipeline.py"""

import json
import re
import sys

import httpx


BASE_URL = "http://localhost:8000/api/v1"

TRAIN_SEATS = [
    ("商务座", "businessClass"),
    ("一等座", "firstClass"),
    ("二等座", "secondClass"),
    ("软卧", "softSleeper"),
    ("硬卧", "hardSleeper"),
    ("硬座", "hardSeat"),
    ("无座", "noSeat"),
]


def request_json(method: str, path: str, **kwargs) -> dict:
    """发起请求并把非 JSON/错误响应打印成可读诊断。"""
    url = f"{BASE_URL}{path}"
    try:
        response = httpx.request(method, url, timeout=30, **kwargs)
    except httpx.RequestError as exc:
        print(f"请求失败：{method} {url}")
        print(f"  {exc}")
        sys.exit(1)

    try:
        payload = response.json()
    except json.JSONDecodeError:
        print(f"接口没有返回 JSON：{method} {url}")
        print(f"  HTTP {response.status_code}")
        print(f"  Content-Type: {response.headers.get('content-type', '-')}")
        print(f"  Body: {response.text[:500] or '<empty>'}")
        sys.exit(1)

    if response.status_code >= 400:
        print(f"接口 HTTP 错误：{method} {url}")
        print(f"  HTTP {response.status_code}")
        print(f"  Body: {json.dumps(payload, ensure_ascii=False)[:500]}")
        sys.exit(1)

    if payload.get("code", 0) != 0:
        print(f"接口业务错误：{method} {url}")
        print(f"  code={payload.get('code')} message={payload.get('message')}")
        sys.exit(1)

    return payload


def _number(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    return float(match.group(0)) if match else 0.0


def _yuan(value) -> str:
    return f"¥{_number(value):.0f}"


def _price(value, empty: str = "价格暂无") -> str:
    amount = _number(value)
    return _yuan(amount) if amount > 0 else empty


def _money(value, empty: str = "费用暂无", approx: bool = False) -> str:
    amount = _number(value)
    if amount <= 0:
        return empty
    prefix = "约" if approx else ""
    return f"{prefix}¥{amount:g}"


def _day_meals(summary: dict, day: dict) -> list[dict]:
    if day.get("meals"):
        return day["meals"]
    for meal_day in summary.get("meal_plan", []):
        if meal_day.get("day") == day.get("day"):
            return meal_day.get("meals", [])
    return []


def _ticket_yuan(value) -> str:
    amount = _number(value)
    if amount <= 0:
        return "票价暂无"
    return f"¥{amount:g}"


def _train_fare(train: dict) -> str:
    prices = train.get("prices") or {}
    seats = []
    for label, key in TRAIN_SEATS:
        availability = train.get(key)
        price = _ticket_yuan(prices.get(label))
        if price == "票价暂无" and (not availability or availability == "--"):
            continue
        seats.append(f"{label} {price} {availability if availability and availability != '--' else '余票暂无'}")
    return " / ".join(seats) if seats else "票价暂无；余票暂无"


def _traffic_option_text(option: dict) -> str:
    detail = option.get("detail", "")
    if option.get("route_type") == "transit" and detail:
        return detail

    time_min = int(_number(option.get("time_min")))
    cost = _money(
        option.get("cost"),
        empty="¥0" if option.get("route_type") == "walking" else "费用暂无",
        approx=bool(option.get("estimated_cost")),
    )
    if time_min > 0:
        return f"{time_min}min {cost}"
    return cost


def stream_message(token: str, session_id: str, content: str, stage: str) -> list[dict]:
    """发送一轮对话并完整消费 SSE，确保服务端完成消息持久化。"""
    events = []
    event_name = "message"
    try:
        stream = httpx.stream(
            "POST",
            f"{BASE_URL}/chat/sessions/{session_id}/messages",
            headers={"Authorization": f"Bearer {token}"},
            json={"content": content},
            timeout=300,
        )
        with stream as response:
            if response.status_code >= 400:
                print(f"{stage}流接口 HTTP 错误：HTTP {response.status_code}")
                print(response.read().decode("utf-8", errors="replace")[:1000])
                sys.exit(1)

            for line in response.iter_lines():
                if line.startswith("event:"):
                    event_name = line[6:].strip() or "message"
                    continue
                if not line.startswith("data:"):
                    continue

                raw_data = line[5:].strip()
                try:
                    data = json.loads(raw_data)
                except json.JSONDecodeError as exc:
                    print(f"{stage} SSE 数据不是合法 JSON：{exc}")
                    print(f"  Data: {raw_data[:500] or '<empty>'}")
                    sys.exit(1)

                if not isinstance(data, dict):
                    print(f"{stage} SSE 数据格式错误：期望对象，实际为 {type(data).__name__}")
                    sys.exit(1)
                if event_name == "error":
                    print(f"{stage}发生错误：{data.get('message') or json.dumps(data, ensure_ascii=False)}")
                    sys.exit(1)

                events.append({"event": event_name, "data": data})
                event_name = "message"
    except httpx.RequestError as exc:
        print(f"{stage}请求失败：{exc}")
        sys.exit(1)

    if not events:
        print(f"{stage}未收到任何 SSE 数据")
        sys.exit(1)
    return events


def print_plan(summary: dict) -> None:
    print(f"\n{'='*50}")
    print(f"  {summary.get('origin','?')} -> {summary.get('destination','?')}  {summary.get('days',0)}天")
    print(f"{'='*50}")

    # ---- 天气预报总览 ----
    weather_forecast = summary.get("weather_forecast", [])
    weather_status = summary.get("weather_status", "")
    if weather_forecast:
        status_note = " (估算天气)" if weather_status == "fallback" else ""
        print(f"\n  [Weather Forecast]{status_note}")
        for fc in weather_forecast:
            print(f"    {fc.get('date','?')}  {fc.get('summary') or fc.get('dayweather','?')}  "
                  f"{fc.get('daywind','')}风{fc.get('daypower','')}级")
    elif weather_status == "fallback":
        print(f"\n  [Weather] 未获取到实时天气，使用中性估算")

    daily_plan = summary.get("daily_itinerary") or summary.get("daily_plan", [])
    if not daily_plan:
        print("\n  [Daily Plan]")
        print("    (接口返回的 daily_itinerary/daily_plan 为空)")

    for day in daily_plan:
        weather_line = ""
        ws = day.get("weather_summary", "")
        if ws:
            weather_line = f"  天气: {ws}"
        print(f"\n  [Day {day['day']}]{weather_line}")
        for attraction in day.get("attractions", []):
            price = _price(attraction.get("price"), "")
            price = f" {price}" if price else ""
            print(f"    - {attraction['name']}{price}  ({attraction.get('reason','')})")
        for meal in _day_meals(summary, day):
            print(f"    {meal['meal']}: {meal['restaurant']} {_price(meal.get('avg_price'))}")
    hotel = summary.get("hotel_plan", {})
    if hotel.get("recommendations"):
        print("\n  [Hotel]")
        for recommendation in hotel["recommendations"][:2]:
            note = " (估算)" if recommendation.get("estimated") else ""
            print(f"    {recommendation['name']} {_price(recommendation.get('price_per_night'))}/night{note}")
        if hotel.get("summary"):
            print(f"    {hotel['summary']}")

    traffic = summary.get("traffic", {})
    if traffic.get("daily_traffic"):
        print(f"\n  [Local Traffic] {_yuan(traffic.get('total_traffic_cost', 0))}")
        for traffic_day in traffic["daily_traffic"]:
            print(
                f"    Day {traffic_day.get('day')}: "
                f"{traffic_day.get('total_time_min', 0)}min {_yuan(traffic_day.get('total_cost', 0))}"
            )
            for segment in traffic_day.get("segments", [])[:3]:
                print(
                    f"      {segment.get('from','?')} -> {segment.get('to','?')} "
                    f"{segment.get('distance_km',0)}km {segment.get('time_min',0)}min "
                    f"{_yuan(segment.get('cost',0))}"
                )
                for index, option in enumerate(segment.get("options", [])[:3], start=1):
                    print(f"        方案{index} {option.get('mode','交通')}: {_traffic_option_text(option)}")
    budget = summary.get("budget", {})
    print(f"\n  [Budget] {_yuan(budget.get('actual_total',0))} / {_yuan(budget.get('total_budget',0))}")
    for item in budget.get("details", []):
        print(
            f"    - {item.get('category','?')}: "
            f"已用 {_yuan(item.get('spent',0))} / 预算 {_yuan(item.get('budget',0))} "
            f"剩余 {_yuan(item.get('remaining',0))} [{item.get('status','ok')}]"
        )
    if budget.get("warnings"):
        print("    Warnings: " + "；".join(budget["warnings"]))
    big_traffic = summary.get("big_traffic") or {}
    if isinstance(big_traffic, dict):
        trains = big_traffic.get("trains") or []
        return_trains = big_traffic.get("return_trains") or []
    elif isinstance(big_traffic, list):
        trains = big_traffic
        return_trains = []
    else:
        trains = []
        return_trains = []
    if trains:
        print(f"\n  [Trains - 去程] {len(trains)} trains")
        for train in trains[:3]:
            from_station = train.get("fromStationName") or train.get("fromStation") or "?"
            to_station = train.get("toStationName") or train.get("toStation") or "?"
            print(
                f"    {train.get('trainCode','?')} {from_station}->{to_station} "
                f"出发 {train.get('departureTime','?')} | "
                f"到达 {train.get('arrivalTime','?')} | "
                f"历时 {train.get('duration','?')} | {_train_fare(train)}"
            )
    if return_trains:
        print(f"\n  [Trains - 返程] {len(return_trains)} trains")
        for train in return_trains[:3]:
            from_station = train.get("fromStationName") or train.get("fromStation") or "?"
            to_station = train.get("toStationName") or train.get("toStation") or "?"
            print(
                f"    {train.get('trainCode','?')} {from_station}->{to_station} "
                f"出发 {train.get('departureTime','?')} | "
                f"到达 {train.get('arrivalTime','?')} | "
                f"历时 {train.get('duration','?')} | {_train_fare(train)}"
            )
    print(f"\n{'='*50}")


def main() -> None:
    print("Login...")
    token = request_json(
        "POST",
        "/auth/sessions",
        json={"method": "phone", "phone": "13700001111", "code": "123456"},
    )["data"]["access_token"]

    print("Create session...")
    sid = request_json(
        "POST",
        "/chat/sessions",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )["data"]["id"]

    # ── Step 1: send travel request ──
    print("Stream pipeline (intent)...\n")
    events = stream_message(token, sid, "武汉出发去北京3天5000,无偏好", "Intent")
    for e in events:
        d = e.get("data", {})
        if "content" in d:
            print(f"Chat: {d['content'][:120]}")
        elif "message" in d:
            print(f"  -> {d['message']}")

    # ── Step 2: auto-confirm ──
    print("\nAuto-confirming...\n")
    events = stream_message(token, sid, "确认", "Confirm")
    print("\nGenerating plan...\n")
    # ── Step 3: print plan from confirmed response ──
    for e in events:
        d = e.get("data", {})
        if "plan_id" in d:
            print_plan(d.get("summary", {}))
        elif "content" in d:
            print(f"Chat: {d['content'][:120]}")
        elif "message" in d:
            print(f"  -> {d['message']}")


if __name__ == "__main__":
    main()
