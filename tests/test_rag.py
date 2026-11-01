import pytest

from app.services.vector import rag as rag_module
from app.services.vector.reranker import RerankerService


@pytest.mark.asyncio
async def test_reranker_disabled_returns_original_order(monkeypatch):
    monkeypatch.setattr("app.services.vector.reranker.settings.RERANKER_ENABLED", False)
    service = RerankerService()

    candidates = [{"id": "1", "document": "a"}, {"id": "2", "document": "b"}]

    result = await service.rerank("query", candidates, top_k=1)

    assert result == candidates[:1]


@pytest.mark.asyncio
async def test_rag_search_runs_recall_then_rerank(monkeypatch):
    async def fake_embed_query(query):
        assert query == "北京历史景点"
        return [0.1, 0.2]

    def fake_search(collection_name, query_embedding, n_results, where=None):
        assert collection_name == "attractions"
        assert query_embedding == [0.1, 0.2]
        assert n_results == 3
        assert where == {"city": "北京"}
        return {
            "ids": [["a", "b"]],
            "documents": [["故宫", "颐和园"]],
            "metadatas": [[{"name": "故宫"}, {"name": "颐和园"}]],
            "distances": [[0.2, 0.4]],
        }

    async def fake_rerank(query, candidates, top_k=None):
        assert query == "北京历史景点"
        assert top_k == 1
        return [candidates[1]]

    monkeypatch.setattr(rag_module.embedding_service, "embed_query", fake_embed_query)
    monkeypatch.setattr(rag_module.vector_store, "search", fake_search)
    monkeypatch.setattr(rag_module.reranker_service, "rerank", fake_rerank)

    result = await rag_module.rag_search(
        "attractions",
        "北京历史景点",
        where={"city": "北京"},
        top_k=3,
        final_k=1,
    )

    expected = {
        "id": "b",
        "document": "颐和园",
        "metadata": {"name": "颐和园"},
        "distance": 0.4,
        "relevance": 0.6,
        "name": "颐和园",
    }
    assert {key: result[0][key] for key in expected} == expected
    assert result[0]["composite_score"] == pytest.approx(0.425)
