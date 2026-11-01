"""
智能体编排全流程测试 — 不走 API，直接跑完整管线

用法:
    python scripts/test_orchestration.py                           # 默认场景
    python scripts/test_orchestration.py --scenario beijing        # 预设场景
    python scripts/test_orchestration.py --scenario all            # 全部场景
    python scripts/test_orchestration.py --city 成都 --days 4 --budget 8000  # 自定义

流程:
    阶段1: UserInteractionAgent → 对话提取参数
    阶段2: pipeline.run_pipeline() → LangGraph 8节点编排
    阶段3: 结果校验 + 可视化输出
"""

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any

# ⚠️ 必须在任何 app.* import 之前强制设置，否则 pydantic Settings 会读 .env 覆盖
os.environ["EMBEDDING_LOCAL_FILES_ONLY"] = "true"
os.environ["RERANKER_LOCAL_FILES_ONLY"] = "true"

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
else:
    # 确保 Linux/Mac 也能正常输出
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.llm.deepseek import DeepSeekLLM

# ================================================================
# 预设场景
# ================================================================

SCENARIOS: dict[str, list[str]] = {
    "beijing": [
        "你好，我想从上海去北京玩3天，预算6000",
        "偏好历史文化，喜欢逛博物馆，节奏适中就行",
        "好的，就按这个方案开始规划吧",
    ],
    "chengdu": [
        "我从武汉出发去成都，4天，预算4000",
        "主要是想吃火锅川菜，还想看看大熊猫，轻松慢游",
        "确认，开始规划",
    ],
    "budget_tight": [
        "去长沙玩2天，从广州出发，预算1500",
        "穷游，能省就省，但是一定要吃好",
        "好的开始吧",
    ],
    "multi_city": [
        "帮我规划一个旅行",
        "从北京出发去杭州，3天，预算5000",
        "喜欢自然风光，节奏轻松一点，酒店要三星级以上就行",
        "确认",
    ],
    "modify": [
        "武汉出发去南京3天5000",
        "偏好改成美食和历史文化，节奏紧凑一点",
        "确认，开始规划",
    ],
}

# ================================================================
# 输出工具
# ================================================================

C = {"R": "\033[91m", "G": "\033[92m", "Y": "\033[93m", "B": "\033[94m",
     "M": "\033[95m", "C": "\033[96m", "W": "\033[97m", "X": "\033[0m",
     "BOLD": "\033[1m"}

TIMINGS: list[tuple[str, float]] = []

def _tick() -> float:
    return time.perf_counter()

def _mark(label: str, start: float) -> None:
    elapsed = (time.perf_counter() - start) * 1000
    TIMINGS.append((label, elapsed))

def _hdr(title: str) -> None:
    print(f"\n{C['BOLD']}{C['C']}{'='*64}{C['X']}")
    print(f"{C['BOLD']}{C['C']}  {title}{C['X']}")
    print(f"{C['BOLD']}{C['C']}{'='*64}{C['X']}\n")

def _sub(title: str) -> None:
    print(f"\n  {C['BOLD']}{C['W']}── {title} ──{C['X']}\n")

def _ok(label: str, value: Any, truncate: int = 300) -> None:
    if isinstance(value, (dict, list)):
        s = json.dumps(value, ensure_ascii=False, indent=2)
    else:
        s = str(value)
    if len(s) > truncate:
        s = s[:truncate] + f"... ({len(s)} chars)"
    print(f"  {C['G']}✓{C['X']} {C['BOLD']}{label}{C['X']}: {s}")

def _err(msg: str) -> None:
    print(f"  {C['R']}✗{C['X']} {C['R']}{msg}{C['X']}")

def _info(msg: str) -> None:
    print(f"  {C['Y']}→{C['X']} {msg}")

def _json(data: Any, max_lines: int = 50) -> None:
    s = json.dumps(data, ensure_ascii=False, indent=2)
    lines = s.split("\n")
    if len(lines) > max_lines:
        print("\n".join(lines[:max_lines]))
        print(f"  {C['Y']}... 截断，共 {len(lines)} 行{C['X']}")
    else:
        print(s)

# ================================================================
# 阶段 1: 对话提取
# ================================================================

async def _phase1_extract(
    messages: list[str],
    scenario_name: str,
) -> dict | None:
    """模拟多轮对话，通过 UserInteractionAgent 提取参数并确认"""
    from app.agents.user_interaction_agent import UserInteractionAgent

    agent = UserInteractionAgent(DeepSeekLLM())
    history: list[dict] = []
    context: dict = {}
    result: dict | None = None

    _sub(f"阶段1: 对话提取 ({scenario_name}, {len(messages)}轮)")

    for idx, msg in enumerate(messages):
        print(f"\n  {C['BOLD']}[轮次 {idx+1}]{C['X']}")
        print(f"  {C['G']}User{C['X']}: {msg}")

        t0 = _tick()
        res = await agent.run({
            "message": msg,
            "history": history,
            "context": context,
        })
        _mark(f"  UI轮次{idx+1}", t0)

        reply = res.get("reply", "")
        print(f"  {C['B']}AI{C['X']}: {reply[:200]}{'...' if len(reply) > 200 else ''}")
        print(f"  {C['Y']}mode={res.get('mode')} status={res.get('status')} "
              f"ready={res.get('ready')} confirmed={res.get('confirmed')}{C['X']}")

        history.append({"role": "user", "content": msg})
        history.append({"role": "assistant", "content": reply})

        if res.get("ready") and res.get("confirmed"):
            result = res
            _ok("提取完成", {k: v for k, v in res.get("extracted", {}).items() if v})

            # 更新 context 模拟真实会话
            context["plan_run_count"] = context.get("plan_run_count", 0) + 1
            context["has_completed_plan"] = True
            context["latest_plan_id"] = f"test_{scenario_name}"
        elif res.get("status") == "collecting":
            _info("等待补充参数...")

    if not result or not result.get("ready"):
        _err("未进入 confirmed 状态，无法触发管线")
        return None

    return result


# ================================================================
# 阶段 2: LangGraph 管线
# ================================================================

async def _phase2_pipeline(extracted: dict) -> dict | None:
    """运行 LangGraph 五阶段管线"""
    from app.orchestrator.pipeline import run_pipeline

    _sub("阶段2: LangGraph 编排")

    pipeline_params = {**extracted, "confirmed": True}
    final_summary: dict | None = None
    events: list[tuple[str, dict]] = []

    t0 = _tick()
    node_timings: dict[str, float] = {}
    current_node: str | None = None
    node_start: float = _tick()

    print(f"  {'事件':20s} {'详情'}")
    print(f"  {'─'*20} {'─'*40}")

    async for evt, data in run_pipeline(pipeline_params):
        events.append((evt, data))

        if evt == "progress":
            # 新节点开始
            step = data.get("step", "?")
            if step != current_node:
                if current_node:
                    node_timings[current_node] = (time.perf_counter() - node_start) * 1000
                current_node = step
                node_start = time.perf_counter()
            pct = data.get("percent", 0)
            bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
            print(f"  {step:20s} {bar} {pct}% {data.get('message', '')}")

        elif evt == "done":
            final_summary = data.get("summary", {})
            _ok("管线完成", f"retry={data.get('retry_count',0)} should_retry={data.get('should_retry',False)}")

        elif evt == "error":
            _err(f"管线错误: {data.get('message', '?')}")
            return None

    # 记录最后一个节点
    if current_node:
        node_timings[current_node] = (time.perf_counter() - node_start) * 1000
    _mark("  管线总计", t0)

    # 打印节点耗时
    if node_timings:
        print(f"\n  {C['Y']}节点耗时:{C['X']}")
        for name, ms in node_timings.items():
            bar = "█" * max(1, int(ms / max(node_timings.values()) * 20))
            print(f"    {name:25s} {bar} {ms:.0f}ms")

    return final_summary


# ================================================================
# 阶段 3: 结果校验 + 可视化
# ================================================================

def _phase3_validate(summary: dict) -> dict[str, Any]:
    """校验 final_plan 的完整性和质量"""
    _sub("阶段3: 结果校验")

    report: dict[str, Any] = {
        "checks": [],
        "warnings": [],
        "score": 0,
        "max_score": 0,
    }

    def check(name: str, condition: bool, weight: int = 1) -> None:
        report["max_score"] += weight
        if condition:
            report["checks"].append(f"✓ {name}")
            report["score"] += weight
        else:
            report["warnings"].append(f"✗ {name}")
            _err(name)
        if condition:
            _ok(name, "通过")

    # 1. 基础字段
    check("destination 非空",    bool(summary.get("destination")), 1)
    check("origin 非空",         bool(summary.get("origin")), 1)
    check("days > 0",            int(summary.get("days", 0)) > 0, 1)
    check("trip_name 非空",      bool(summary.get("trip_name")), 1)

    # 2. 行程
    itinerary = summary.get("daily_itinerary") or summary.get("daily_plan", [])
    check("daily_itinerary 非空", len(itinerary) > 0, 3)
    check("天数匹配",              len(itinerary) == int(summary.get("days", 0)), 2)

    total_attrs = 0
    total_meals = 0
    coord_missing = 0
    for day in itinerary:
        attrs = day.get("attractions", [])
        total_attrs += len(attrs)
        for a in attrs:
            if not (a.get("latitude") and a.get("longitude")):
                coord_missing += 1
            if not a.get("name"):
                coord_missing += 1
        meals = day.get("meals", [])
        total_meals += len(meals)

    check("每天有景点",    total_attrs > 0, 2)
    check(f"景点数≥天数 ({total_attrs}个)", total_attrs >= len(itinerary), 1)
    check("每天有餐饮",    total_meals > 0, 1)
    check(f"坐标覆盖率",   coord_missing == 0, 3)

    if coord_missing > 0:
        print(f"    {C['Y']}⚠{C['X']} {coord_missing} 个景点缺少坐标")

    # 3. 预算
    budget = summary.get("budget", {})
    check("budget 存在",       bool(budget), 1)
    check("total_budget > 0",  float(budget.get("total_budget", 0)) > 0, 1)
    check("actual_total >= 0", float(budget.get("actual_total", 0)) >= 0, 1)

    per_person = float(budget.get("per_person_per_day", 0))
    check("人均/天 合理",      0 < per_person < 10000, 1)
    if per_person > 0:
        _ok("人均/天", f"¥{per_person:.2f}")

    warnings_list = budget.get("warnings", [])
    if warnings_list:
        print(f"    {C['Y']}预算警告:{C['X']}")
        for w in warnings_list:
            print(f"      {w}")

    # 4. 交通
    traffic = summary.get("traffic", {})
    check("traffic 存在",    bool(traffic), 1)
    daily_traffic = traffic.get("daily_traffic", [])
    check("每天有交通",       len(daily_traffic) > 0, 1)
    total_traf_cost = float(traffic.get("total_cost", 0))
    check("交通费合理",       total_traf_cost >= 0, 1)

    # 5. 酒店
    hotel = summary.get("hotel_plan", {})
    check("hotel_plan 存在",  bool(hotel), 1)
    recs = hotel.get("recommendations", [])
    check("有酒店推荐",        len(recs) > 0, 1)
    if recs:
        _ok("酒店候选", f"{len(recs)} 个, TOP1: {recs[0].get('name', '?')}")

    # 6. 详情
    attr_details = summary.get("attraction_details", [])
    check("attraction_details", len(attr_details) >= 0, 1)

    # 评分
    score = report["score"]
    max_s = report["max_score"]
    grade = "A" if score >= max_s * 0.9 else "B" if score >= max_s * 0.7 else "C" if score >= max_s * 0.5 else "D"
    print(f"\n  {C['BOLD']}评分: {score}/{max_s} ({grade}){C['X']}")
    if report["warnings"]:
        print(f"  {C['Y']}未通过: {', '.join(report['warnings'])}{C['X']}")

    return report


# ================================================================
# 可视化输出
# ================================================================

def _phase4_render(summary: dict) -> None:
    """将 final_plan 渲染为可读摘要"""
    _sub("阶段4: 行程可视化")

    dest = summary.get("destination", "?")
    origin = summary.get("origin", "?")
    days = summary.get("days", 0)
    trip_name = summary.get("trip_name", f"{dest}{days}日之旅")

    # 头部
    print(f"""
  {C['BOLD']}{C['M']}╔{'═'*56}╗
  ║ {trip_name:^54} ║
  ║ {origin + ' → ' + dest + '  ·  ' + str(days) + '天':^54} ║
  ╚{'═'*56}╝{C['X']}
""")

    # 行程配置
    cfg = summary.get("trip_config", {})
    tags = []
    if cfg.get("pace"):      tags.append(cfg["pace"])
    if cfg.get("travelers"): tags.append(f"{cfg['travelers']}人")
    if cfg.get("preferences"): tags.append("、".join(cfg["preferences"][:3]))
    print(f"  {C['Y']}配置{C['X']}: {' | '.join(tags)}")
    print(f"  {C['Y']}预算{C['X']}: ¥{cfg.get('total_budget', 0):.0f}  "
          f"酒店≤¥{cfg.get('hotel_budget', 0):.0f}/晚  餐饮≤¥{cfg.get('meal_budget', 0):.0f}/人\n")

    # 每日行程
    itinerary = summary.get("daily_itinerary") or summary.get("daily_plan", [])
    for day in itinerary:
        d = day.get("day", "?")
        print(f"  {C['BOLD']}{C['B']}┌─ Day {d} {'─'*50}{C['X']}")

        # 景点
        for a in day.get("attractions", []):
            price = "免费" if a.get("price", 0) == 0 else f"¥{a.get('price', 0):.0f}"
            dur = f"{a.get('duration_hours', '?')}h" if a.get('duration_hours') else ""
            coords = ""
            if a.get("latitude") and a.get("longitude"):
                coords = f" ({a['latitude']:.4f}, {a['longitude']:.4f})"
            print(f"  │ {C['G']}📍{C['X']} {C['BOLD']}{a.get('name', '?')}{C['X']}  "
                  f"{C['Y']}{price}{C['X']}  {dur}{coords}")
            if a.get("reason"):
                print(f"  │   {a['reason'][:80]}")

        # 餐饮
        for m in day.get("meals", []):
            print(f"  │ {C['M']}🍽{C['X']} {m.get('meal', '?')}: {m.get('restaurant', '?')}  "
                  f"{C['Y']}¥{m.get('avg_price', '?')}{C['X']}")
            if m.get("reason"):
                print(f"  │   {m['reason'][:80]}")

        print(f"  {C['B']}└{'─'*56}{C['X']}\n")

    # 酒店
    hotel = summary.get("hotel_plan", {})
    recs = hotel.get("recommendations", [])
    if recs:
        print(f"  {C['BOLD']}{C['B']}🏨 酒店{C['X']}")
        for r in recs[:3]:
            star = "★" * r.get("star", 3)
            cs = r.get("commute_score", 0)
            print(f"    {r.get('name', '?')}  {star}  ¥{r.get('price_per_night', '?')}/晚  "
                  f"评分{r.get('rating', '?')}  通勤{cs:.0%}")
        print()

    # 交通
    traffic = summary.get("traffic", {})
    if traffic.get("daily_traffic"):
        print(f"  {C['BOLD']}{C['B']}🚇 市内交通  总费用: ¥{traffic.get('total_cost', 0):.0f}{C['X']}")
        for d in traffic["daily_traffic"]:
            segs = d.get("segments", [])
            print(f"    Day{d['day']}: {d['total_time_min']}min  ¥{d['total_cost']}  ({len(segs)}段)")
            for i, seg in enumerate(segs):
                from_name = seg.get('from', '?')[:24]
                to_name = seg.get('to', '?')[:24]
                mode = seg.get('mode', '')
                hotel_tag = f" {C['G']}<<< 回酒店{C['X']}" if (i == len(segs) - 1 and '酒店' in to_name) else ""
                print(f"      {from_name:24s} -> {to_name:24s}  "
                      f"{seg.get('distance_km',0):5.1f}km  {seg.get('time_min',0):4d}min  "
                      f"¥{seg.get('cost',0):.0f}  {mode}{hotel_tag}")
        print()

    # 城际交通
    big = summary.get("big_traffic", {})
    if big.get("city_distance_km"):
        mode = big.get("recommend_mode", "train")
        dist = big.get("city_distance_km", 0)
        trains = big.get("trains", [])
        print(f"  {C['BOLD']}{C['B']}🚄 城际交通  {origin}⇄{dest}  {dist}km  建议: {mode}{C['X']}")
        if isinstance(trains, list):
            for t in trains[:3]:
                print(f"    {t.get('trainCode','?')}  {t.get('departureTime','?')}-{t.get('arrivalTime','?')}  {t.get('duration','?')}")

    # 预算明细
    budget = summary.get("budget", {})
    if budget.get("details"):
        print(f"\n  {C['BOLD']}{C['B']}💰 预算明细  总计: ¥{budget.get('actual_total', 0):.0f} / ¥{budget.get('total_budget', 0):.0f}{C['X']}")
        print(f"  {'类别':8s} {'预算':>10s} {'实际':>10s} {'剩余':>10s} {'状态'}")
        print(f"  {'─'*8} {'─'*10} {'─'*10} {'─'*10} {'─'*6}")
        for d in budget["details"]:
            status_icon = "✓" if d.get("status") == "ok" else "⚠" if d.get("status") == "over" else "?"
            print(f"  {d.get('category','?'):8s} ¥{d.get('budget',0):>9.0f} ¥{d.get('spent',0):>9.0f} "
                  f"¥{d.get('remaining',0):>9.0f} {status_icon}")
        print()

    # 详情
    attr_details = summary.get("attraction_details", [])
    if attr_details:
        print(f"  {C['BOLD']}{C['B']}📝 景点详情 ({len(attr_details)}条){C['X']}")
        for d in attr_details[:5]:
            tips = d.get("tips", [])
            if isinstance(tips, str): tips = [tips]
            spots = d.get("famous_spots", [])
            if isinstance(spots, str): spots = [spots]
            print(f"    {d.get('name','?')}")
            if tips:   print(f"      💡 {'; '.join(tips[:2])}")
            if spots:  print(f"      🔍 {'; '.join(spots[:2])}")

    _ok("attraction_details 条数", len(attr_details))

    food_details = summary.get("food_details", [])
    if food_details:
        print(f"\n  {C['BOLD']}{C['B']}🍳 餐饮详情 ({len(food_details)}条){C['X']}")
        for d in food_details[:5]:
            dishes = d.get("signature_dishes", [])
            if isinstance(dishes, str): dishes = [dishes]
            print(f"    {d.get('name','?')}: {'、'.join(dishes[:3]) if dishes else '?'}")
    _ok("food_details 条数", len(food_details))


# ================================================================
# 主流程
# ================================================================

async def run_scenario(name: str, messages: list[str]) -> dict | None:
    _hdr(f"场景: {name}")

    overall_start = _tick()

    # 阶段1: 对话提取
    phase1_start = _tick()
    result = await _phase1_extract(messages, name)
    _mark("阶段1 总计", phase1_start)
    if not result:
        return None

    extracted = result.get("extracted", {})
    print(f"\n  {C['Y']}提取参数: {json.dumps({k:v for k,v in extracted.items() if v}, ensure_ascii=False)}{C['X']}")

    # 阶段2: 管线编排
    phase2_start = _tick()
    final = await _phase2_pipeline(extracted)
    _mark("阶段2 总计", phase2_start)
    if not final:
        return None

    # 阶段3: 校验
    phase3_start = _tick()
    report = _phase3_validate(final)
    _mark("阶段3 总计", phase3_start)

    # 阶段4: 可视化
    phase4_start = _tick()
    _phase4_render(final)
    _mark("阶段4 总计", phase4_start)

    _mark("全部总计", overall_start)

    # 耗时汇总
    print(f"\n  {C['BOLD']}{C['C']}⏱ 耗时汇总{C['X']}")
    print(f"  {'─'*40} {'─'*12}")
    total_ms = 0
    for label, ms in TIMINGS:
        if label.startswith("  "):
            print(f"  {label:40s} {ms:>8.0f}ms")
        else:
            print(f"\n  {C['BOLD']}{label:40s} {ms:>8.0f}ms{C['X']}")
        total_ms += ms

    TIMINGS.clear()  # 每个场景独立计时
    return {"final_plan": final, "report": report}


async def run_custom(city: str, origin: str = "武汉", days: int = 3, budget: float = 5000,
                      preferences: str = "轻松慢游", pace: str = "适中"):
    """跳过对话提取，直接用参数跑管线"""
    _hdr(f"自定义: {origin}→{city} {days}天 ¥{budget:.0f}")

    extracted = {
        "destination": city,
        "origin": origin,
        "days": days,
        "total_budget": budget,
        "planning_budget": budget,
        "reserve_budget": 0.0,
        "preferences": [p.strip() for p in preferences.split(",")],
        "preferences_provided": True,
        "pace": pace,
        "hotel_star": 3,
        "hotel_budget": min(500, budget * 0.3),
        "meal_budget": min(100, budget * 0.06),
        "travelers": 1,
        "budget_no_limit": False,
    }

    _ok("参数", {k: v for k, v in extracted.items() if v})

    final = await _phase2_pipeline(extracted)
    if not final:
        return None

    report = _phase3_validate(final)
    _phase4_render(final)
    return {"final_plan": final, "report": report}


async def main():
    parser = argparse.ArgumentParser(description="智能体编排全流程测试")
    parser.add_argument("--scenario", "-s", choices=list(SCENARIOS) + ["all"],
                        help="预设场景")
    parser.add_argument("--city", "-c", help="目的地")
    parser.add_argument("--origin", default="武汉", help="出发地 (默认: 武汉)")
    parser.add_argument("--days", type=int, default=3, help="天数 (默认: 3)")
    parser.add_argument("--budget", "-b", type=float, default=5000, help="预算 (默认: 5000)")
    parser.add_argument("--prefs", default="轻松慢游", help="偏好，逗号分隔")
    parser.add_argument("--pace", default="适中", help="节奏: 紧凑/适中/轻松")
    parser.add_argument("--skip-extract", action="store_true",
                        help="跳过对话提取，直接用 CLI 参数跑管线")
    args = parser.parse_args()

    # 决定跑哪些场景
    to_run: list[tuple[str, list[str] | None]] = []

    if args.city and (args.skip_extract or not args.scenario):
        # 自定义参数直跑
        result = await run_custom(
            city=args.city, origin=args.origin, days=args.days,
            budget=args.budget, preferences=args.prefs, pace=args.pace,
        )
        if result:
            report = result["report"]
            score = report["score"]
            max_s = report["max_score"]
            grade = "A" if score >= max_s * 0.9 else "B" if score >= max_s * 0.7 else "C" if score >= max_s * 0.5 else "D"
            print(f"\n{C['BOLD']}{C['C']}最终评分: {score}/{max_s} ({grade}){C['X']}\n")
        return

    if args.scenario == "all":
        for name, msgs in SCENARIOS.items():
            to_run.append((name, msgs))
    elif args.scenario:
        to_run.append((args.scenario, SCENARIOS[args.scenario]))
    else:
        # 默认跑第一个场景
        name = list(SCENARIOS)[0]
        print(f"{C['Y']}未指定场景，使用默认: {name}{C['X']}")
        print(f"可用场景: {', '.join(SCENARIOS)}")
        print(f"或使用 --city 自定义\n")
        to_run.append((name, SCENARIOS[name]))

    # 执行
    all_reports = []
    for name, msgs in to_run:
        result = await run_scenario(name, msgs)
        if result:
            all_reports.append(result)

    # 汇总
    if len(all_reports) > 1:
        _hdr(f"全部场景汇总 ({len(all_reports)}个)")
        for i, r in enumerate(all_reports):
            report = r["report"]
            fp = r["final_plan"]
            score = report["score"]
            max_s = report["max_score"]
            print(f"  {i+1}. {fp.get('trip_name','?'):20s}  评分: {score}/{max_s}  人均/天: ¥{fp.get('budget',{}).get('per_person_per_day',0):.0f}")

    print()


if __name__ == "__main__":
    asyncio.run(main())
