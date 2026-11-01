"""
V2.0 行程执行链路测试 — 不走 API，直连 Agent

测试项:
  ❶ TripAgent:      启动行程 → 签到打卡 → 进度追踪 → 提醒生成
  ❷ AdjustAgent:    天气调整 / 时间漂移 / 预算告警
  ❸ TravelogueAgent: 游记生成 (diary/xiaohongshu/guide) + 社交素材 + 照片标注

用法:
    python scripts/test_v2_execution.py
    python scripts/test_v2_execution.py --skip-pipeline  # 用内置 mock，跳过管线
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Any

os.environ["EMBEDDING_LOCAL_FILES_ONLY"] = "true"
os.environ["RERANKER_LOCAL_FILES_ONLY"] = "true"

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.llm.deepseek import DeepSeekLLM

C = {"R": "\033[91m", "G": "\033[92m", "Y": "\033[93m", "B": "\033[94m",
     "M": "\033[95m", "C": "\033[96m", "W": "\033[97m", "X": "\033[0m",
     "BOLD": "\033[1m"}

# ============================================================
# Mock 数据 — 模拟管线产出的 final_plan（景点带 tags/category）
# ============================================================

MOCK_FINAL_PLAN = {
    "trip_name": "杭州2日之旅", "summary": "武汉出发，杭州2日游",
    "destination": "杭州", "origin": "武汉", "days": 2,
    "trip_config": {
        "destination": "杭州", "origin": "武汉", "days": 2,
        "total_budget": 4000.0, "planning_budget": 4000.0, "reserve_budget": 0.0,
        "preferences": ["轻松慢游"], "pace": "适中", "hotel_star": 3,
        "hotel_budget": 500.0, "meal_budget": 100.0, "travelers": 1,
    },
    "daily_itinerary": [
        {"day": 1,
         "attractions": [
             {"name": "西湖", "price": 0, "duration_hours": 3.0,
              "latitude": 30.2427, "longitude": 120.1464, "address": "杭州市西湖区",
              "category": "风景名胜;公园广场;公园", "tags": ["自然风光","山水","湖泊","免费","户外"]},
             {"name": "灵隐寺", "price": 75, "duration_hours": 2.0,
              "latitude": 30.2491, "longitude": 120.1032, "address": "杭州市西湖区法云弄1号",
              "category": "风景名胜;风景名胜;寺庙教堂", "tags": ["历史人文","宗教","古建筑"]},
             {"name": "河坊街", "price": 0, "duration_hours": 1.5,
              "latitude": 30.2432, "longitude": 120.1748, "address": "杭州市上城区",
              "category": "购物服务;步行街", "tags": ["购物","美食","老街","免费"]},
         ],
         "meals": [
             {"meal": "午餐", "restaurant": "楼外楼", "avg_price": 120,
              "latitude": 30.2520, "longitude": 120.1420, "address": "孤山路30号"},
             {"meal": "晚餐", "restaurant": "知味观", "avg_price": 80,
              "latitude": 30.2480, "longitude": 120.1680, "address": "仁和路83号"},
         ]},
        {"day": 2,
         "attractions": [
             {"name": "龙井村", "price": 0, "duration_hours": 2.5,
              "latitude": 30.2214, "longitude": 120.1113, "address": "杭州市西湖区龙井路",
              "category": "风景名胜;公园广场;公园", "tags": ["自然风光","茶园","户外","免费"]},
             {"name": "九溪烟树", "price": 0, "duration_hours": 2.0,
              "latitude": 30.2005, "longitude": 120.1126, "address": "杭州市西湖区",
              "category": "风景名胜;风景名胜;风景名胜", "tags": ["自然风光","山水","徒步","户外","免费"]},
         ],
         "meals": [
             {"meal": "午餐", "restaurant": "绿茶餐厅(龙井店)", "avg_price": 85,
              "latitude": 30.2200, "longitude": 120.1120, "address": "龙井路83号"},
             {"meal": "晚餐", "restaurant": "外婆家", "avg_price": 65,
              "latitude": 30.2500, "longitude": 120.1600, "address": "湖滨路3号"},
         ]},
    ],
    "meal_plan": [
        {"day": 1, "meals": [
            {"meal": "午餐", "restaurant": "楼外楼", "avg_price": 120},
            {"meal": "晚餐", "restaurant": "知味观", "avg_price": 80},
        ]},
        {"day": 2, "meals": [
            {"meal": "午餐", "restaurant": "绿茶餐厅(龙井店)", "avg_price": 85},
            {"meal": "晚餐", "restaurant": "外婆家", "avg_price": 65},
        ]},
    ],
    "hotel_plan": {
        "recommendations": [
            {"name": "杭州西湖亚朵酒店", "latitude": 30.2500, "longitude": 120.1550,
             "price_per_night": 350, "total": 350, "rating": 4.7, "star": 4},
        ],
        "selected_hotel": {"name": "杭州西湖亚朵酒店"},
    },
    "traffic": {
        "daily_traffic": [
            {"day": 1, "segments": [
                {"from": "杭州站", "to": "酒店", "distance_km": 5.0, "time_min": 20, "cost": 3.0, "mode": "transit"},
            ], "total_time_min": 60, "total_cost": 6.0},
            {"day": 2, "segments": [
                {"from": "酒店", "to": "杭州站", "distance_km": 5.0, "time_min": 20, "cost": 3.0, "mode": "transit"},
            ], "total_time_min": 80, "total_cost": 8.0},
        ],
        "total_cost": 14.0, "time_warnings": [],
    },
    "big_traffic": {
        "trains": [{"trainCode": "G1435", "departureTime": "07:53", "arrivalTime": "12:35", "duration": "04:42"}],
        "flights": [], "recommend_mode": "train", "city_distance_km": 598.2,
        "arrival_hub": {"name": "杭州站", "lat": 30.2435, "lng": 120.1829, "type": "station"},
    },
    "budget": {
        "total": 4000, "total_budget": 4000,
        "actual_total": 700, "remaining": 3300,
        "per_person_per_day": 350.0,
        "allocation": {"住宿": 1383, "交通": 935, "餐饮": 748, "门票": 561, "购物": 374},
        "details": [
            {"category": "住宿", "budget": 1383, "spent": 350, "remaining": 1033, "status": "ok"},
            {"category": "交通", "budget": 935, "spent": 14, "remaining": 921, "status": "ok"},
            {"category": "餐饮", "budget": 748, "spent": 350, "remaining": 398, "status": "ok"},
            {"category": "门票", "budget": 561, "spent": 75, "remaining": 486, "status": "ok"},
        ],
        "warnings": [],
    },
}

# 模拟签到 — planned_time(key 名匹配 TripAgent 代码)
MOCK_CHECKINS = [
    {
        "source_day": 1, "poi_type": "attraction", "poi_name": "西湖",
        "lat": 30.2427, "lng": 120.1464,
        "planned_time": "09:00",
        "actual_at": datetime(2026, 7, 12, 9, 45),  # 迟到45min
        "planned_cost": 0, "actual_cost": 60,
        "rating": 5, "note": "清晨的西湖太美了，苏堤漫步了快两个小时",
        "photos": [
            {"url": "https://example.com/photo_xihu_1.jpg", "width": 4000, "height": 3000, "ai_caption": "西湖晨雾中的断桥"},
            {"url": "https://example.com/photo_xihu_2.jpg", "width": 3000, "height": 2000, "ai_caption": "苏堤春晓全景"},
        ],
    },
    {
        "source_day": 1, "poi_type": "restaurant", "poi_name": "楼外楼",
        "lat": 30.2520, "lng": 120.1420,
        "planned_time": "12:00",
        "actual_at": datetime(2026, 7, 12, 12, 30),  # 迟到30min
        "planned_cost": 120, "actual_cost": 150,
        "rating": 4, "note": "西湖醋鱼名不虚传，但排队等了半小时",
        "photos": [{"url": "https://example.com/photo_food_1.jpg", "width": 2000, "height": 2000}],
    },
    {
        "source_day": 2, "poi_type": "attraction", "poi_name": "龙井村",
        "lat": 30.2214, "lng": 120.1113,
        "planned_time": "10:00",
        "actual_at": datetime(2026, 7, 13, 9, 58),  # 提前2min
        "planned_cost": 0, "actual_cost": 120,
        "rating": 5, "note": "亲自采了龙井茶，还买了两斤带回家",
        "photos": [{"url": "https://example.com/photo_longjing_1.jpg", "width": 4000, "height": 3000}],
    },
]

# ============================================================
# 输出工具
# ============================================================

def _hdr(title: str) -> None:
    print(f"\n{C['BOLD']}{C['C']}{'='*64}{C['X']}")
    print(f"{C['BOLD']}{C['C']}  {title}{C['X']}")
    print(f"{C['BOLD']}{C['C']}{'='*64}{C['X']}\n")

def _sub(title: str) -> None:
    print(f"\n  {C['BOLD']}{C['W']}── {title} ──{C['X']}")

def _ok(label: str, value: Any, truncate: int = 300) -> None:
    s = json.dumps(value, ensure_ascii=False, indent=2) if isinstance(value, (dict, list)) else str(value)
    if len(s) > truncate:
        s = s[:truncate] + f"... ({len(s)} chars)"
    print(f"  {C['G']}✓{C['X']} {C['BOLD']}{label}{C['X']}: {s}")

def _info(msg: str) -> None:
    print(f"  {C['Y']}→{C['X']} {msg}")

def _warn(msg: str) -> None:
    print(f"  {C['Y']}⚠{C['X']} {msg}")


# ============================================================
# ❶ TripAgent
# ============================================================

async def test_trip_agent(final_plan: dict):
    _hdr("❶ TripAgent — 行程执行")
    from app.agents.trip_agent import TripAgent

    agent = TripAgent(DeepSeekLLM())

    # 1a. 启动行程
    _sub("1a. 启动行程")
    t0 = time.time()
    start_res = await agent.run({"action": "start", **final_plan})
    _ok("status", start_res.get("status", "?"))
    _ok("total_pois", start_res.get("total_pois", 0))
    _ok("started_at", str(start_res.get("started_at", ""))[:19])
    _ok("预算快照", f"¥{start_res.get('budget_total', 0):.0f}")

    daily_breakdown = start_res.get("daily_breakdown", {})
    for d, pois in sorted(daily_breakdown.items()) if isinstance(daily_breakdown, dict) else []:
        print(f"    Day{d}: {', '.join(pois)}")

    elapsed = (time.time() - t0) * 1000
    trip_id = start_res.get("trip_id", "mock_trip_001")
    print(f"  {C['Y']}⏱{C['X']} {elapsed:.0f}ms")

    # 1b. 模拟签到
    _sub("1b. 签到打卡 (3次)")
    checkin_results = []
    for ci, c in enumerate(MOCK_CHECKINS):
        t0 = time.time()
        _info(f"签到 {ci+1}: {c['poi_name']} ({c['poi_type']})")
        res = await agent.run({
            "action": "checkin",
            "trip_id": trip_id,
            "poi_type": c["poi_type"],
            "poi_name": c["poi_name"],
            "lat": c.get("lat"), "lng": c.get("lng"),
            "photos": c.get("photos", []),
            "planned_time": c.get("planned_time", ""),  # ← 匹配 Agent 的 key
            "actual_at": c.get("actual_at"),
            "planned_cost": c.get("planned_cost"),
            "actual_cost": c.get("actual_cost"),
            "rating": c.get("rating"),
            "note": c.get("note"),
        })
        checkin_results.append(res)
        delta = res.get("time_delta_min", 0)
        status = f"{C['G']}准时{C['X']}" if abs(delta) <= 15 else f"{C['R']}偏差{delta}min{C['X']}"
        _ok("时间", f"计划 {c['planned_time']} → 实际 {str(c['actual_at'])[11:16]}  {status}")
        _ok("花费差异", f"计划 ¥{c['planned_cost']} → 实际 ¥{c['actual_cost']}")
        _ok("触发调整", f"{res.get('trigger_adjustment', False)} ({res.get('trigger_reason', '')})")

    # 1c. 进度
    _sub("1c. 进度追踪")
    progress = await agent.run({
        "action": "progress",
        "total_pois": start_res.get("total_pois", 6),
        "checked_in": len(checkin_results),
        "current_day": 2,
        "total_days": 2,
    })
    _ok("进度", f"{progress.get('checked_in', '?')}/{progress.get('total_pois', '?')}")
    _ok("POI完成度", f"{progress.get('poi_progress_pct', 0):.1f}%")
    _ok("整体进度", f"{progress.get('overall_pct', 0):.1f}%")
    _ok("超前?", progress.get("ahead", False))

    # 1d. 提醒
    _sub("1d. 明日提醒")
    reminder = await agent.run({
        "action": "reminder",
        "tomorrow_day": 2,
        "destination": "杭州",
        "day_outline": {"stops": [
            {"name": "龙井村", "type": "attraction", "planned_time": "09:00"},
            {"name": "九溪烟树", "type": "attraction", "planned_time": "14:00"},
            {"name": "外婆家", "type": "restaurant", "planned_time": "18:00"},
        ]},
        "weather": {"temp_high": 32, "temp_low": 24, "weather": "晴", "advice": "注意防晒"},
    })
    reminder_text = (reminder.get("reminder_text", "") or "")[:200]
    _ok("提醒", reminder_text)
    _ok("首站", f"{reminder.get('first_stop', '?')} @ {reminder.get('first_stop_time', '?')}")
    _ok("天气建议", reminder.get("weather_advice", ""))
    _ok("打包提示", reminder.get("packing_hint", ""))

    return {"trip_id": trip_id, "start_res": start_res, "checkins": checkin_results}


# ============================================================
# ❷ AdjustAgent
# ============================================================

async def test_adjust_agent(destination: str):
    _hdr("❷ AdjustAgent — 动态调整")
    from app.agents.adjust_agent import AdjustAgent

    agent = AdjustAgent(DeepSeekLLM())

    # 2a. 天气调整
    _sub("2a. 暴雨 → 室内替代")
    _info("模拟: Day1 暴雨预警，户外景点(西湖/河坊街)应被替换")
    t0 = time.time()
    weather_res = await agent.run({
        "trigger_type": "weather",
        "weather_type": "暴雨",
        "affected_days": [1],
        "destination": destination,
        "daily_plan": MOCK_FINAL_PLAN["daily_itinerary"],
        "preferences": ["轻松慢游"],
    })
    _ok("trigger_type", weather_res.get("trigger_type", "?"))
    adjs = weather_res.get("adjustments", [])
    _ok("调整数", len(adjs))
    for adj in adjs[:3]:
        print(f"    {adj.get('original','?')} → {adj.get('alternative','?')} ({adj.get('reason','?')})")
    print(f"  {C['Y']}⏱{C['X']} {(time.time()-t0)*1000:.0f}ms")

    # 2b. 时间漂移
    _sub("2b. 迟到2h → 压缩后面行程")
    _info("模拟: Day2 第一站迟到了2小时，后面景点要被压缩或砍掉")
    t0 = time.time()
    drift_res = await agent.run({
        "trigger_type": "time_drift",
        "drift_min": 120,
        "affected_day": 2, "current_day": 2,
        "destination": destination,
        "today_plan": MOCK_FINAL_PLAN["daily_itinerary"][1],
        "remaining_stops": [
            {"name": "九溪烟树", "type": "attraction", "duration_hours": 2.0, "rating": 4.8},
        ],
        "hotel_plan": MOCK_FINAL_PLAN["hotel_plan"],
        "preferences": ["轻松慢游"],
    })
    _ok("trigger_type", drift_res.get("trigger_type", "?"))
    removed = drift_res.get("removed_stops", [])
    _ok("移除站点", len(removed))
    _ok("原因", drift_res.get("reason", "?"))
    for r in removed:
        print(f"    移除: {r}")
    print(f"  {C['Y']}⏱{C['X']} {(time.time()-t0)*1000:.0f}ms")

    # 2c. 预算告警
    _sub("2c. 预算超支 → 降级建议")
    _info("模拟: 已花费¥2500/预算¥4000，剩余1天只有¥1500")
    t0 = time.time()
    budget_res = await agent.run({
        "trigger_type": "budget_alert",
        "total_budget": 4000,
        "budget_total": 4000,
        "budget_spent": 2500,
        "budget_per_day": 1000,
        "remaining_days": 1,
        "destination": destination,
        "daily_plan": MOCK_FINAL_PLAN["daily_itinerary"],
        "hotel_plan": MOCK_FINAL_PLAN["hotel_plan"],
    })
    _ok("trigger_type", budget_res.get("trigger_type", "?"))
    suggestions = budget_res.get("suggestions", [])
    _ok("建议数", len(suggestions))
    _ok("原因", budget_res.get("reason", "?"))
    for s in suggestions[:5]:
        if "daily_budget_remaining" in s:
            print(f"    剩余每天: ¥{s.get('daily_budget_remaining', 0):.0f}")
        else:
            print(f"    {s.get('action','?')}: {s.get('detail','?')}")
    print(f"  {C['Y']}⏱{C['X']} {(time.time()-t0)*1000:.0f}ms")


# ============================================================
# ❸ TravelogueAgent
# ============================================================

async def test_travelogue_agent():
    _hdr("❸ TravelogueAgent — 游记 + 社交素材")
    from app.agents.travelogue_agent import TravelogueAgent

    agent = TravelogueAgent(DeepSeekLLM())

    # 3a. 游记生成 (3 种风格)
    for style in ["diary", "xiaohongshu", "guide"]:
        _sub(f"3a. 游记 — {style}")
        t0 = time.time()
        res = await agent.run({
            "action": "generate",
            "style": style,
            "trip_info": MOCK_FINAL_PLAN["trip_config"],
            "checkins": MOCK_CHECKINS,
        })
        _ok("标题", res.get("title", "?"))
        content = res.get("content", "") or ""
        _ok("内容", content[:250])
        _ok("总POI", res.get("total_pois", 0))
        _ok("照片", res.get("total_photos", 0))
        print(f"  {C['Y']}⏱{C['X']} {(time.time()-t0)*1000:.0f}ms")

    # 3b. 社交素材
    _sub("3b. 社交素材生成 (9宫格+卡片+合集+预算卡)")
    t0 = time.time()
    mat_res = await agent.run({
        "action": "generate_materials",
        "trip_info": {**MOCK_FINAL_PLAN["trip_config"], "trip_id": "mock_trip_001"},
        "checkins": MOCK_CHECKINS,
    })
    mats = mat_res.get("materials", [])
    type_counts = {}
    for m in mats:
        if m:
            t = m.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1
            _ok(t, (m.get("title", "") or m.get("content", ""))[:80])
    _ok("素材种类", type_counts)
    print(f"  {C['Y']}⏱{C['X']} {(time.time()-t0)*1000:.0f}ms")

    # 3c. 照片标注
    _sub("3c. 照片 AI 标注")
    t0 = time.time()
    anno_res = await agent.run({
        "action": "annotate_photos",
        "checkin": MOCK_CHECKINS[0],
    })
    photos = anno_res.get("photos", [])
    for p in photos[:3]:
        print(f"    {p.get('ai_caption', '?')[:80]}")
        print(f"    标签: {', '.join(p.get('ai_tags', [])[:5])}  质量: {p.get('quality_score', '?')}")
    print(f"  {C['Y']}⏱{C['X']} {(time.time()-t0)*1000:.0f}ms")


# ============================================================
# 主流程
# ============================================================

async def main():
    parser = argparse.ArgumentParser(description="V2.0 行程执行链路测试")
    parser.add_argument("--skip-pipeline", action="store_true",
                        help="跳过管线，直接用内置 mock 数据测试")
    parser.add_argument("--city", default="杭州", help="如果用管线，目的地 (默认: 杭州)")
    parser.add_argument("--days", type=int, default=2)
    parser.add_argument("--budget", type=float, default=4000)
    args = parser.parse_args()

    final_plan = MOCK_FINAL_PLAN
    destination = args.city

    if not args.skip_pipeline:
        _info("先跑管线获取 final_plan...")
        from app.orchestrator.pipeline import run_pipeline

        extracted = {
            "destination": args.city, "origin": "武汉", "days": args.days,
            "total_budget": args.budget, "planning_budget": args.budget,
            "reserve_budget": 0.0, "preferences": ["轻松慢游"],
            "preferences_provided": True, "pace": "适中",
            "hotel_star": 3, "hotel_budget": min(500, args.budget * 0.3),
            "meal_budget": min(100, args.budget * 0.06), "travelers": 1,
            "budget_no_limit": False,
        }

        async for evt, data in run_pipeline({**extracted, "confirmed": True}):
            if evt == "done":
                s = data.get("summary", {})
                if s:
                    final_plan = s
                    destination = s.get("destination", args.city)
                    _ok("管线完成", f"{destination} {s.get('days',0)}天")
                    break

    # 测试
    await test_trip_agent(final_plan)
    await test_adjust_agent(destination)
    await test_travelogue_agent()

    _hdr("测试完成")
    print(f"  ❶ TripAgent:      启动+签到(时间/花费偏差)+进度+提醒")
    print(f"  ❷ AdjustAgent:    暴雨/迟到/超支 3 种调整")
    print(f"  ❸ TravelogueAgent: 3 风格游记 + 6 种社交素材 + 照片标注")
    print()


if __name__ == "__main__":
    asyncio.run(main())
