"""
Shared RAG retrieval helper.

The pipeline is:
    query -> embedding -> Chroma Top-K recall -> optional reranker -> final K
"""

import asyncio
import logging
import time
from typing import Any

from app.config import settings
from app.services.vector.embedding import embedding_service
from app.services.vector.reranker import reranker_service
from app.services.vector.vector_store import vector_store


logger = logging.getLogger(__name__)


async def rag_search(
    collection_name: str,
    query: str,
    where: dict | None = None,
    top_k: int | None = None,
    final_k: int | None = None,
    use_reranker: bool | None = None,
    preferences: list[str] | None = None,
    max_price: float = 0,
    min_rating: float = 0,
) -> list[dict[str, Any]]:
    """
    RAG 检索 + 综合评分

    评分权重: 语义相关度(50%) + 评分(25%) + 标签匹配(15%) + 价格(10%)
    """
    final_limit = max(1, final_k or settings.RAG_FINAL_K)
    recall_limit = max(final_limit, top_k or settings.RAG_TOP_K)

    started_at = time.perf_counter()
    logger.info(
        "[RAG.search] start collection=%s recall=%d final=%d",
        collection_name,
        recall_limit,
        final_limit,
    )
    try:
        query_embedding = await embedding_service.embed_query(query)

        recall_started_at = time.perf_counter()
        result = await asyncio.to_thread(
            vector_store.search,
            collection_name,
            query_embedding,
            n_results=recall_limit,
            where=where,
        )
        logger.info(
            "[RAG.recall] collection=%s elapsed=%.2fs",
            collection_name,
            time.perf_counter() - recall_started_at,
        )

        candidates = _build_candidates(result)
        if not candidates:
            return []

        rerank_enabled = settings.RERANKER_ENABLED if use_reranker is None else use_reranker
        if rerank_enabled:
            candidates = await reranker_service.rerank(query, candidates, top_k=final_limit)
        else:
            candidates = candidates[:final_limit]

        # 综合评分
        from app.services.vector.scorer import composite_score
        candidates = composite_score(
            candidates,
            preferences=preferences,
            max_price=max_price,
            min_rating=min_rating,
        )
        return candidates
    except Exception:
        logger.exception("[RAG.search] failed collection=%s", collection_name)
        raise
    finally:
        logger.info(
            "[RAG.search] end collection=%s elapsed=%.2fs",
            collection_name,
            time.perf_counter() - started_at,
        )


def _build_candidates(result: dict[str, Any]) -> list[dict[str, Any]]:
    ids = _first_row(result, "ids")
    metadatas = _first_row(result, "metadatas")
    documents = _first_row(result, "documents")
    distances = _first_row(result, "distances")

    candidates: list[dict[str, Any]] = []
    for index, item_id in enumerate(ids):
        metadata = metadatas[index] if index < len(metadatas) and metadatas[index] else {}
        if not isinstance(metadata, dict):
            metadata = {}

        distance = distances[index] if index < len(distances) else None
        document = documents[index] if index < len(documents) else ""

        candidate = {
            "id": item_id,
            "document": document or "",
            "metadata": metadata,
            "distance": distance,
            "relevance": _distance_to_relevance(distance),
            **metadata,
        }
        candidate.setdefault("name", item_id)
        candidates.append(candidate)

    return candidates


def _first_row(result: dict[str, Any], key: str) -> list:
    rows = result.get(key, [[]])
    if not rows:
        return []
    first = rows[0]
    return first if isinstance(first, list) else []


def _distance_to_relevance(distance: Any) -> float:
    if distance is None:
        return 0.0
    try:
        return round(1 - float(distance), 4)
    except (TypeError, ValueError):
        return 0.0
