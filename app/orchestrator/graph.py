"""
LangGraph — 两轮决策工作流

    parallel → decision_r1 (定景点+餐厅) → detail → decision_r2 (选最优酒店)
    → traffic (完整交通规划) → budget
                                          │
                               ┌──────────┴──────────┐
                               │ route_after_budget() │
                               └──────────┬──────────┘
                                    done  │  retry
                                     END  │
                                    ┌─────┘
                                    ▼
                                 adjust
                                    │
                                    ▼
                              parallel (重跑)
"""

from langgraph.graph import END, StateGraph

from app.orchestrator.nodes import (
    node_adjust_params,
    node_budget,
    node_decision_r1,
    node_decision_r2,
    node_detail_enrich,
    node_parallel_planning,
    node_traffic,
    node_weather,
    route_after_budget,
)
from app.orchestrator.state import PlannerState


def build_graph() -> StateGraph:
    w = StateGraph(PlannerState)

    w.add_node("fetch_weather", node_weather)
    w.add_node("parallel_planning", node_parallel_planning)
    w.add_node("decision_r1", node_decision_r1)
    w.add_node("detail_enrich", node_detail_enrich)
    w.add_node("plan_traffic", node_traffic)
    w.add_node("decision_r2", node_decision_r2)
    w.add_node("budget", node_budget)
    w.add_node("adjust", node_adjust_params)

    w.set_entry_point("fetch_weather")

    # weather → parallel planning
    w.add_edge("fetch_weather", "parallel_planning")

    # R1: 定稿景点+餐厅
    w.add_edge("parallel_planning", "decision_r1")
    w.add_edge("decision_r1", "detail_enrich")

    # R2: 轻量交通评估后选酒店，再基于最终酒店跑完整交通
    w.add_edge("detail_enrich", "decision_r2")
    w.add_edge("decision_r2", "plan_traffic")
    w.add_edge("plan_traffic", "budget")

    # 预算循环
    w.add_conditional_edges("budget", route_after_budget, {
        "done": END,
        "retry": "adjust",
    })
    w.add_edge("adjust", "parallel_planning")

    return w.compile()


planner_graph = build_graph()
