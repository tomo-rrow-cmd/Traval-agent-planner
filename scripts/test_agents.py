"""
Agent 单测脚本 — 不走 API，直接调智能体

用法:
    python scripts/test_agents.py                      # 交互式选择
    python scripts/test_agents.py --agent attraction   # 测单个
    python scripts/test_agents.py --agent all          # 全量测试
    python scripts/test_agents.py --agent traffic --city 南京

可用 Agent:
    ui              UserInteractionAgent — 对话意图识别 + 参数提取
    attraction      AttractionAgent — 景点搜索 + 规划
    food            FoodAgent — 餐厅搜索 + 规划
    hotel           HotelAgent — 酒店搜索 + 推荐
    traffic         TrafficAgent — 交通路径规划
    budget          BudgetAgent — 预算核算 + 最终方案
    decision        DecisionAgent — 两轮决策 R1+R2
    detail          DetailAgent — 景点/餐饮深度详情
    weather         WeatherAgent — 天气查询 + 建议
    adjust          AdjustAgent — 天气/时间/预算动态调整
    travelogue      TravelogueAgent — 游记生成 + 社交素材
    trip            TripAgent — 行程执行 + 签到
"""

import argparse
import asyncio
import json
import os
import sys
import time
from typing import Any

# Windows GBK 编码兼容
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ⚠️ 必须在任何 app.* import 之前强制设置
os.environ["EMBEDDING_LOCAL_FILES_ONLY"] = "true"
os.environ["RERANKER_LOCAL_FILES_ONLY"] = "true"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.llm.deepseek import DeepSeekLLM

# ================================================================
# 颜色输出
# ================================================================

C = {"R": "\033[91m", "G": "\033[92m", "Y": "\033[93m", "B": "\033[94m",
     "M": "\033[95m", "C": "\033[96m", "W": "\033[97m", "X": "\033[0m",
     "BOLD": "\033[1m"}

def _hdr(title: str) -> None:
    print(f"\n{C['BOLD']}{C['C']}{'='*60}{C['X']}")
    print(f"{C['BOLD']}{C['C']}  {title}{C['X']}")
    print(f"{C['BOLD']}{C['C']}{'='*60}{C['X']}\n")

def _ok(label: str, value: Any, truncate: int = 200) -> None:
    s = json.dumps(value, ensure_ascii=False, indent=2) if not isinstance(value, str) else value
    if len(s) > truncate:
        s = s[:truncate] + f"... ({len(s)} chars total)"
    print(f"  {C['G']}✓{C['X']} {C['BOLD']}{label}{C['X']}: {s}")

def _err(label: str, msg: str) -> None:
    print(f"  {C['R']}✗{C['X']} {label}: {C['R']}{msg}{C['X']}")

def _info(msg: str) -> None:
    print(f"  {C['Y']}→{C['X']} {msg}")

def _json_block(data: dict | list, max_lines: int = 40) -> None:
    s = json.dumps(data, ensure_ascii=False, indent=2)
    lines = s.split("\n")
    if len(lines) > max_lines:
        print("\n".join(lines[:max_lines]))
        print(f"  {C['Y']}... 截断，共 {len(lines)} 行{C['X']}")
    else:
        print(s)

# ================================================================
# 共享 LLM
# ================================================================

_llm = None

def get_llm():
    global _llm
    if _llm is None:
        _llm = DeepSeekLLM()
    return _llm

# ================================================================
# Mock 数据
# ================================================================

MOCK_TRIP_CONFIG = {
    "destination": "南京", "origin": "武汉", "days": 3,
    "total_budget": 5000.0, "planning_budget": 5000.0, "reserve_budget": 0.0,
    "preferences": ["轻松慢游"], "pace": "慢", "hotel_star": 3,
    "hotel_budget": 500.0, "meal_budget": 100.0, "travelers": 1,
    "budget_no_limit": False, "preferences_provided": True,
}

MOCK_DAILY_PLAN = [
    {
        "day": 1, "attractions": [
            {"name": "南京博物院", "latitude": 32.0408, "longitude": 118.8251, "price": 0, "duration_hours": 3.0},
            {"name": "琵琶湖公园", "latitude": 32.0541, "longitude": 118.8248, "price": 0, "duration_hours": 1.5},
            {"name": "东南大学", "latitude": 32.0542, "longitude": 118.7952, "price": 0, "duration_hours": 1.5},
        ],
        "meals": [
            {"meal": "午餐", "restaurant": "雅苑酒家", "avg_price": 62, "latitude": 32.0536, "longitude": 118.7966},
            {"meal": "晚餐", "restaurant": "鸽味轩", "avg_price": 91, "latitude": 32.0602, "longitude": 118.7871},
        ],
    },
    {
        "day": 2, "attractions": [
            {"name": "红山森林动物园", "latitude": 32.0918, "longitude": 118.8029, "price": 0, "duration_hours": 3.0},
            {"name": "南京大学", "latitude": 32.0552, "longitude": 118.7796, "price": 0, "duration_hours": 1.5},
        ],
        "meals": [
            {"meal": "午餐", "restaurant": "刘长兴", "avg_price": 28, "latitude": 32.0602, "longitude": 118.7870},
            {"meal": "晚餐", "restaurant": "王鼎有鱼", "avg_price": 80, "latitude": 32.0608, "longitude": 118.7884},
        ],
    },
]

MOCK_HOTEL_PLAN = {
    "recommendations": [
        {"name": "南京金陵饭店", "latitude": 32.0510, "longitude": 118.7850,
         "price_per_night": 450, "total": 1350, "rating": 4.8, "star": 5},
        {"name": "如家快捷(鼓楼店)", "latitude": 32.0600, "longitude": 118.7900,
         "price_per_night": 180, "total": 540, "rating": 4.2, "star": 3},
    ],
    "selected_hotel": {"name": "如家快捷(鼓楼店)"},
}

MOCK_MEAL_PLAN = [
    {"day": 1, "meals": [
        {"meal": "午餐", "restaurant": "雅苑酒家", "avg_price": 62},
        {"meal": "晚餐", "restaurant": "鸽味轩", "avg_price": 91},
    ]},
    {"day": 2, "meals": [
        {"meal": "午餐", "restaurant": "刘长兴", "avg_price": 28},
        {"meal": "晚餐", "restaurant": "王鼎有鱼", "avg_price": 80},
    ]},
]

MOCK_TRAFFIC = {
    "daily_traffic": [
        {"day": 1, "segments": [
            {"from": "酒店", "to": "南京博物院", "distance_km": 3.5, "time_min": 15, "cost": 2.0, "mode": "transit"},
        ], "total_time_min": 45, "total_cost": 8.0},
    ],
    "total_traffic_cost": 8.0, "time_warnings": [],
    "big_traffic": {"trains": [], "flights": [], "recommend_mode": "train", "city_distance_km": 540},
}

MOCK_CHECKINS = [
    {"source_day": 1, "poi_type": "attraction", "poi_name": "南京博物院",
     "rating": 5, "note": "展品太震撼了，逛了三个小时都不够",
     "photos": [{"url": "https://example.com/photo1.jpg", "ai_caption": "南京博物院正门"}]},
    {"source_day": 1, "poi_type": "restaurant", "poi_name": "雅苑酒家",
     "rating": 4, "note": "盐水鸭好吃，性价比很高"},
    {"source_day": 2, "poi_type": "attraction", "poi_name": "红山森林动物园",
     "rating": 5, "note": "看到了考拉！动物园设计得很用心"},
]

# ================================================================
# Agent 测试函数
# ================================================================

async def test_ui_agent(interactive: bool = False):
    """UserInteractionAgent — 对话意图识别 + 参数提取"""
    from app.agents.user_interaction_agent import UserInteractionAgent

    agent = UserInteractionAgent(get_llm())

    # 非交互式：跑几个典型场景
    test_cases = [
        ("直接规划", "你好，我想从武汉去南京玩3天，预算5000，喜欢轻松慢游"),
        ("闲聊", "南京有什么好吃的？"),
        ("确认", "好的，就按这个方案开始规划吧"),
        ("修改参数", "预算改成3000吧"),
    ]

    for label, msg in test_cases:
        _info(f"测试: {label}")
        print(f"    输入: {msg}")
        t0 = time.time()
        res = await agent.run({
            "message": msg,
            "history": [{"role": "user", "content": "你好"}],
            "context": {},
        })
        elapsed = (time.time() - t0) * 1000
        _ok("mode",       res.get('mode', '?'))
        _ok("status",     res.get('status', '?'))
        _ok("ready",      res.get('ready', '?'))
        _ok("confirmed",  res.get('confirmed', '?'))
        _ok("extracted",  res.get('extracted', {}))
        _ok("reply",      res.get('reply', '')[:150])
        print(f"  {C['Y']}⏱{C['X']} {elapsed:.0f}ms\n")


async def test_attraction_agent(city: str = "北京"):
    """AttractionAgent — RAG 搜索真实景点 + LLM 规划"""
    from app.agents.attraction_agent import AttractionAgent

    agent = AttractionAgent(get_llm())
    _info(f"搜索 {city} 景点 (RAG → LLM 规划)...")
    t0 = time.time()
    res = await agent.run({
        "destination": city, "days": 2, "preferences": ["历史文化"],
        "pace": "适中",
    })
    elapsed = (time.time() - t0) * 1000
    _ok("candidate_count", res.get("candidate_count", 0))
    dp = res.get("daily_plan", [])
    for day in dp:
        names = [a["name"] for a in day.get("attractions", [])]
        has_coords = sum(1 for a in day.get("attractions", []) if a.get("latitude") and a.get("longitude"))
        print(f"  Day{day.get('day')}: {', '.join(names)}")
        print(f"         坐标覆盖率: {has_coords}/{len(names)}")
    print(f"  {C['Y']}⏱{C['X']} {elapsed:.0f}ms\n")


async def test_food_agent(city: str = "北京"):
    """FoodAgent — RAG 搜索餐厅 + LLM 规划"""
    from app.agents.food_agent import FoodAgent

    agent = FoodAgent(get_llm())
    _info(f"搜索 {city} 餐厅...")
    t0 = time.time()
    res = await agent.run({
        "destination": city, "days": 2,
        "cuisine_preferences": ["火锅", "川菜"],
        "meal_budget": 100,
    })
    elapsed = (time.time() - t0) * 1000
    mp = res.get("meal_plan", [])
    for day in mp:
        meals = day.get("meals", [])
        for m in meals:
            print(f"  Day{day.get('day')} {m.get('meal')}: {m.get('restaurant')} ¥{m.get('avg_price')}")
    print(f"  {C['Y']}⏱{C['X']} {elapsed:.0f}ms\n")


async def test_hotel_agent(city: str = "北京"):
    """HotelAgent — 酒店搜索 + 推荐"""
    from app.agents.hotel_agent import HotelAgent

    agent = HotelAgent(get_llm())
    _info(f"搜索 {city} 酒店...")
    t0 = time.time()
    res = await agent.run({
        "destination": city, "days": 3,
        "hotel_star_min": 3, "budget_per_night": 500,
    })
    elapsed = (time.time() - t0) * 1000
    hp = res.get("hotel_plan", {})
    recs = hp.get("recommendations", [])
    for r in recs[:5]:
        print(f"  {r.get('name')} | ★{r.get('star', '?')} | ¥{r.get('price_per_night', '?')}/晚 | 评分{r.get('rating', '?')}")
    _ok("候选总数", len(recs))
    print(f"  {C['Y']}⏱{C['X']} {elapsed:.0f}ms\n")


async def test_traffic_agent(city: str = "南京"):
    """TrafficAgent — 高德路径规划 + 大交通"""
    from app.agents.traffic_agent import TrafficAgent

    agent = TrafficAgent(get_llm())
    _info(f"规划 {city} 市内交通...")
    t0 = time.time()
    res = await agent.run({
        "destination": city, "origin": "武汉", "days": 2,
        "daily_locations": MOCK_DAILY_PLAN,
        "meal_plan": MOCK_MEAL_PLAN,
        "hotel_plan": MOCK_HOTEL_PLAN,
        "preferred_transport": "地铁",
    })
    elapsed = (time.time() - t0) * 1000
    _ok("总交通费",    f"¥{res.get('total_traffic_cost', 0)}")
    _ok("时间警告",    res.get("time_warnings", []))
    _ok("酒店匹配分",  res.get("hotel_match", {}).get("score", "?"))
    _ok("大交通建议",  res.get("big_traffic", {}).get("recommend_mode", "?"))
    for d in res.get("daily_traffic", []):
        print(f"  Day{d['day']}: {d['total_time_min']}min ¥{d['total_cost']} ({len(d.get('segments',[]))}段)")
    print(f"  {C['Y']}⏱{C['X']} {elapsed:.0f}ms\n")


async def test_budget_agent():
    """BudgetAgent — 预算核算 + final_plan 组装"""
    from app.agents.budget_agent import BudgetAgent

    agent = BudgetAgent(get_llm())

    # 构造完整输入（模拟 node_budget 的状态）
    expenses = {"hotels": 540, "traffic": 18, "meals": 500, "attractions": 0}

    _info("核算预算 + 组装 final_plan...")
    t0 = time.time()
    res = await agent.run({
        "total_budget": 5000, "planning_budget": 5000, "reserve_budget": 0,
        "days": 3, "travelers": 1,
        "destination": "南京", "origin": "武汉",
        "preferences": ["轻松慢游"], "pace": "慢",
        "hotel_star": 3, "hotel_budget": 500, "meal_budget": 100,
        "budget_no_limit": False, "preferences_provided": True,
        "expenses": expenses,
        "daily_itinerary": MOCK_DAILY_PLAN,
        "meal_plan": MOCK_MEAL_PLAN,
        "hotel_plan": MOCK_HOTEL_PLAN,
        "traffic": MOCK_TRAFFIC,
        "attraction_details": [],
        "food_details": [],
        "retry_count": 0,
        "adjusted_params": {},
    })
    elapsed = (time.time() - t0) * 1000

    fp = res.get("final_plan", {})
    _ok("超支%",       f"{res.get('over_pct', 0)}%")
    _ok("应重试",      res.get("should_retry", False))
    _ok("人均/天",     f"¥{res.get('per_person_per_day', 0)}")
    _ok("总费用",      f"¥{res.get('actual_total', 0)}")
    _ok("final_plan keys", list(fp.keys()))
    bp = res.get("budget_plan", {})
    if bp.get("details"):
        print("  预算明细:")
        for d in bp["details"]:
            print(f"    {d['category']}: 预算¥{d['budget']} | 实际¥{d['spent']} | {d['status']}")
    print(f"  {C['Y']}⏱{C['X']} {elapsed:.0f}ms\n")


async def test_decision_agent():
    """DecisionAgent — 两轮决策 R1(定稿景点+餐厅) + R2(交通选酒店)"""
    from app.agents.decision_agent import DecisionAgent

    agent = DecisionAgent(get_llm())

    # Round 1
    _info("R1: 定稿景点+餐厅...")
    t0 = time.time()
    r1 = await agent.run_round1({
        "daily_plan": MOCK_DAILY_PLAN,
        "meal_plan": MOCK_MEAL_PLAN,
    })
    _ok("stage",   r1.get("stage", "?"))
    _ok("needs_decision", r1.get("decision_needed", False))
    for day in r1.get("daily_plan", []):
        print(f"  Day{day['day']}: {len(day.get('attractions',[]))}景点 + {len(day.get('meals',[]))}餐")
    print(f"  {C['Y']}⏱{C['X']} {(time.time()-t0)*1000:.0f}ms\n")

    # Round 2
    _info("R2: 交通评估后选最优酒店...")
    t0 = time.time()
    r2 = await agent.run_round2({
        "hotel_plan": MOCK_HOTEL_PLAN,
        "daily_plan": r1.get("daily_plan", MOCK_DAILY_PLAN),
        "destination": "南京",
    })
    _ok("selected", r2.get("hotel_plan", {}).get("selected", "?"))
    recs = r2.get("hotel_plan", {}).get("recommendations", [])
    for r in recs:
        print(f"  {r.get('name')}: commute_score={r.get('commute_score', '?')}")
    print(f"  {C['Y']}⏱{C['X']} {(time.time()-t0)*1000:.0f}ms\n")


async def test_detail_agent():
    """DetailAgent — 景点深度详情 + 餐饮招牌菜"""
    from app.agents.detail_agent import DetailAgent

    agent = DetailAgent(get_llm())

    _info("获取景点详情 + 招牌菜...")
    t0 = time.time()
    res = await agent.run({
        "daily_plan": MOCK_DAILY_PLAN,
        "meal_plan": MOCK_MEAL_PLAN,
        "destination": "南京",
    })
    elapsed = (time.time() - t0) * 1000
    ad = res.get("attraction_details", [])
    fd = res.get("food_details", [])
    _ok("attraction_details",  len(ad))
    _ok("food_details",        len(fd))
    for d in ad[:3]:
        print(f"  景点: {d.get('name')} | tips={d.get('tips', '?')}")
    for d in fd[:3]:
        print(f"  餐厅: {d.get('name')} | 招牌={d.get('signature_dishes', '?')}")
    print(f"  {C['Y']}⏱{C['X']} {elapsed:.0f}ms\n")


async def test_weather_agent(city: str = "北京"):
    """WeatherAgent — 天气查询 + 建议"""
    from app.agents.weather_agent import WeatherAgent

    agent = WeatherAgent(get_llm())
    _info(f"查询 {city} 天气...")
    t0 = time.time()
    res = await agent.run({
        "destination": city,
        "start_date": "2026-07-12",
        "end_date": "2026-07-14",
        "daily_itinerary": MOCK_DAILY_PLAN,
    })
    elapsed = (time.time() - t0) * 1000
    _ok("suggestions", res.get("suggestions", [])[:2])
    wd = res.get("weather_data", {})
    _ok("current",     wd.get("current", {}))
    _ok("forecasts",   len(wd.get("forecasts", [])))
    print(f"  {C['Y']}⏱{C['X']} {elapsed:.0f}ms\n")


async def test_adjust_agent():
    """AdjustAgent — 天气/时间/预算触发调整"""
    from app.agents.adjust_agent import AdjustAgent

    agent = AdjustAgent(get_llm())

    _info("测试: 天气调整 (暴雨 → 室内替代)...")
    t0 = time.time()
    res = await agent.run({
        "trigger_type": "weather",
        "weather_type": "暴雨",
        "affected_days": [1],
        "destination": "南京",
        "daily_plan": MOCK_DAILY_PLAN,
        "preferences": ["轻松慢游"],
    })
    elapsed = (time.time() - t0) * 1000
    _ok("trigger",          res.get("trigger_type", "?"))
    _ok("adjustments",      len(res.get("adjustments", [])))
    for adj in res.get("adjustments", [])[:3]:
        print(f"  {adj.get('original', '?')} → {adj.get('alternative', '?')} ({adj.get('reason', '?')})")
    print(f"  {C['Y']}⏱{C['X']} {elapsed:.0f}ms\n")


async def test_travelogue_agent():
    """TravelogueAgent — 游记生成 + 社交素材"""
    from app.agents.travelogue_agent import TravelogueAgent

    agent = TravelogueAgent(get_llm())

    # 游记
    _info("生成游记 (diary 风格)...")
    t0 = time.time()
    res = await agent.run({
        "action": "generate",
        "style": "diary",
        "trip_info": MOCK_TRIP_CONFIG,
        "checkins": MOCK_CHECKINS,
    })
    elapsed = (time.time() - t0) * 1000
    _ok("title",        res.get("title", "?"))
    _ok("content",      (res.get("content", "") or res.get("markdown", ""))[:300])
    _ok("cover_url",    res.get("cover_url", "?"))
    print(f"  {C['Y']}⏱{C['X']} {elapsed:.0f}ms\n")

    # 社交素材
    _info("生成社交素材 (9宫格 + 朋友圈卡片)...")
    t0 = time.time()
    res2 = await agent.run({
        "action": "generate_materials",
        "trip_info": MOCK_TRIP_CONFIG,
        "checkins": MOCK_CHECKINS,
    })
    mats = res2.get("materials", [])
    for m in mats:
        print(f"  [{m.get('type')}] {m.get('title', '?')}")
    print(f"  {C['Y']}⏱{C['X']} {(time.time()-t0)*1000:.0f}ms\n")


async def test_trip_agent():
    """TripAgent — 行程执行 + 签到 + 进度"""
    from app.agents.trip_agent import TripAgent

    agent = TripAgent(get_llm())

    final_plan = {
        **MOCK_TRIP_CONFIG,
        "daily_itinerary": MOCK_DAILY_PLAN,
        "daily_plan": MOCK_DAILY_PLAN,
    }

    # start
    _info("开始行程...")
    res = await agent.run({"action": "start", **final_plan})
    _ok("status",     res.get("status", "?"))
    _ok("total_pois", res.get("total_pois", 0))

    # checkin
    _info("处理签到...")
    res = await agent.run({
        "action": "checkin",
        "poi_type": "attraction", "poi_name": "南京博物院",
        "actual_at": "2026-07-12T10:30:00",
        "planned_at": "09:00", "rating": 5,
        "note": "展品很震撼",
    })
    _ok("时间偏差(min)", res.get("time_delta_min", "?"))

    # reminder
    _info("生成提醒...")
    res = await agent.run({
        "action": "reminder",
        "tomorrow_day": 2, "destination": "南京",
        "tomorrow_itinerary": MOCK_DAILY_PLAN[0],
    })
    _ok("reminder_text", (res.get("reminder_text", "") or "")[:200])
    print()


# ================================================================
# 主入口
# ================================================================

AGENT_MAP = {
    "ui":         ("UserInteractionAgent",  test_ui_agent),
    "attraction": ("AttractionAgent",       test_attraction_agent),
    "food":       ("FoodAgent",             test_food_agent),
    "hotel":      ("HotelAgent",            test_hotel_agent),
    "traffic":    ("TrafficAgent",          test_traffic_agent),
    "budget":     ("BudgetAgent",           test_budget_agent),
    "decision":   ("DecisionAgent",         test_decision_agent),
    "detail":     ("DetailAgent",           test_detail_agent),
    "weather":    ("WeatherAgent",          test_weather_agent),
    "adjust":     ("AdjustAgent",           test_adjust_agent),
    "travelogue": ("TravelogueAgent",       test_travelogue_agent),
    "trip":       ("TripAgent",             test_trip_agent),
}

CITY_AGENTS = {"attraction", "food", "hotel", "traffic", "weather"}


async def main():
    parser = argparse.ArgumentParser(description="Agent 单测脚本")
    parser.add_argument("--agent", "-a", choices=list(AGENT_MAP) + ["all"],
                        help="选择要测试的 Agent")
    parser.add_argument("--city",  "-c", default="南京",
                        help="测试用的城市 (默认: 南京)")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="UI Agent 交互式对话模式")
    args = parser.parse_args()

    # ---- 选择 Agent ----
    selected = args.agent
    if not selected:
        _hdr("可选 Agent")
        for k, (name, _) in AGENT_MAP.items():
            print(f"  {C['BOLD']}{k:15s}{C['X']} {name}")
        print()
        selected = input(f"  输入 agent 名 (all=全部): ").strip()
        if not selected:
            print("  已取消")
            return

    if selected == "all":
        targets = list(AGENT_MAP.keys())
    else:
        targets = [s.strip() for s in selected.split(",") if s.strip() in AGENT_MAP]
        if not targets:
            print(f"  未知 Agent: {selected}")
            print(f"  可选: {', '.join(AGENT_MAP)}")
            return

    _hdr(f"Agent 测试 — {len(targets)} 个")

    for key in targets:
        name, fn = AGENT_MAP[key]
        print(f"\n{C['BOLD']}{C['M']}▸ {name}{C['X']}")
        print(f"  {'─'*50}")

        try:
            if key == "ui" and args.interactive:
                # 交互式 UI Agent
                await _interactive_ui()
            elif key in CITY_AGENTS:
                await fn(city=args.city)
            else:
                await fn()
        except Exception as e:
            _err("FAILED", str(e))
            import traceback
            traceback.print_exc()

    # ---- 汇总 ----
    _hdr("完成")
    print(f"  测试了 {len(targets)} 个 Agent\n")


async def _interactive_ui():
    """交互式 UserInteractionAgent 对话"""
    from app.agents.user_interaction_agent import UserInteractionAgent

    agent = UserInteractionAgent(get_llm())
    history = []
    context = {"session_status": "active"}

    print(f"  {C['Y']}输入消息开始对话，Ctrl+C 退出{C['X']}\n")

    # 开场
    res = await agent.run({"message": "你好", "history": [], "context": context})
    print(f"  {C['B']}AI{C['X']}: {res['reply']}")
    history.append({"role": "assistant", "content": res["reply"]})

    while True:
        try:
            msg = input(f"\n  {C['G']}You{C['X']}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  已退出\n")
            break
        if not msg:
            continue

        res = await agent.run({"message": msg, "history": history, "context": context})
        print(f"  {C['B']}AI{C['X']}: {res['reply']}")
        print(f"  {C['Y']}mode={res.get('mode')} status={res.get('status')} ready={res.get('ready')}{C['X']}")
        history.append({"role": "user", "content": msg})
        history.append({"role": "assistant", "content": res["reply"]})


if __name__ == "__main__":
    asyncio.run(main())
