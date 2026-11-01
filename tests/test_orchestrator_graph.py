"""测试 LangGraph 编排顺序。"""


def test_decision_r2_runs_before_full_traffic():
    from app.orchestrator.graph import build_graph

    graph = build_graph().get_graph()
    edges = {(edge.source, edge.target) for edge in graph.edges}

    assert ("detail_enrich", "decision_r2") in edges
    assert ("decision_r2", "plan_traffic") in edges
    assert ("plan_traffic", "budget") in edges
    assert ("detail_enrich", "plan_traffic") not in edges
    assert ("plan_traffic", "decision_r2") not in edges
