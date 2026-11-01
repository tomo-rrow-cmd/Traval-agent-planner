"""
Agent 测试脚本 — 输入文本，看 UserInteractionAgent 的提取结果

用法: python scripts/test_agent.py
"""

import asyncio, json, sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.llm.deepseek import DeepSeekLLM
from app.agents.user_interaction_agent import UserInteractionAgent


def _plan_summary_from_extracted(extracted: dict) -> dict:
    budget = {
        "total_budget": extracted.get("total_budget", 0),
        "reserve_budget": extracted.get("reserve_budget", 0),
        "planning_budget": extracted.get("planning_budget", 0),
    }
    trip_config = {
        "destination": extracted.get("destination", ""),
        "origin": extracted.get("origin", ""),
        "days": extracted.get("days", 0),
        "total_budget": extracted.get("total_budget", 0),
        "reserve_budget": extracted.get("reserve_budget", 0),
        "planning_budget": extracted.get("planning_budget", 0),
        "budget_no_limit": extracted.get("budget_no_limit", False),
        "preferences": extracted.get("preferences", []),
        "preferences_provided": extracted.get("preferences_provided", False),
        "pace": extracted.get("pace", "适中"),
        "hotel_star": extracted.get("hotel_star", 3),
        "hotel_budget": extracted.get("hotel_budget", 500),
        "meal_budget": extracted.get("meal_budget", 100),
        "travelers": extracted.get("travelers", 1),
        "budget": budget,
    }
    return {
        "destination": extracted.get("destination", ""),
        "origin": extracted.get("origin", ""),
        "days": extracted.get("days", 0),
        "preferences": extracted.get("preferences", []),
        "preferences_provided": extracted.get("preferences_provided", False),
        "pace": extracted.get("pace", "适中"),
        "hotel_star": extracted.get("hotel_star", 3),
        "hotel_budget": extracted.get("hotel_budget", 500),
        "meal_budget": extracted.get("meal_budget", 100),
        "travelers": extracted.get("travelers", 1),
        "budget": budget,
        "trip_config": trip_config,
    }


async def main():
    llm = DeepSeekLLM()
    agent = UserInteractionAgent(llm)
    history = []
    context = {
        "session_status": "active",
        "latest_plan_id": "",
        "has_completed_plan": False,
        "plan_run_count": 0,
    }

    print("=" * 45)
    print("  Agent Test — Ctrl+C to quit")
    print("=" * 45)

    # Welcome
    res = await agent.run({"message": "hello", "history": [], "context": context})
    print(f"\n  AI: {res['reply']}")
    history.append({"role": "assistant", "content": res["reply"]})

    while True:
        try:
            msg = input("\n  You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye")
            break
        if not msg:
            continue

        res = await agent.run({"message": msg, "history": history, "context": context})

        print(f"\n  AI: {res['reply']}")
        print(f"  ─────────────────────────────")
        print(f"  mode:       {res.get('mode')}")
        print(f"  status:     {res.get('status')}")
        print(f"  extracted:  {json.dumps(res['extracted'], ensure_ascii=False)}")
        print(f"  ready:      {res['ready']}")

        history.append({"role": "user", "content": msg})
        history.append({"role": "assistant", "content": res["reply"]})
        if res.get("ready"):
            context["plan_run_count"] += 1
            context["session_status"] = "completed"
            context["has_completed_plan"] = True
            context["latest_plan_id"] = f"local_run_{context['plan_run_count']}"
            context["latest_plan_summary"] = _plan_summary_from_extracted(res["extracted"])


if __name__ == "__main__":
    asyncio.run(main())
