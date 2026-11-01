"""
Cross-encoder reranker for the second stage of RAG retrieval.

Flow: vector Top-K recall -> reranker scores query/document pairs -> final K.
The service is intentionally lazy-loaded so offline tests and endpoints that do
not use RAG do not download or initialize the model.
"""

import logging
import time
from pathlib import Path
from typing import Any, Optional

from app.config import settings
from app.services.vector.runtime import run_model_operation


logger = logging.getLogger(__name__)


class RerankerService:
    """ModelScope-backed BGE reranker with a safe fallback."""

    def __init__(self):
        self._model: Optional[object] = None

    def _lazy_load(self) -> None:
        if self._model is not None:
            return
        if not settings.RERANKER_ENABLED:
            self._model = False
            return

        try:
            from modelscope import snapshot_download
            from sentence_transformers import CrossEncoder

            cache_dir = Path(settings.RERANKER_MODEL_CACHE_DIR)
            cache_dir.mkdir(parents=True, exist_ok=True)

            model_dir = snapshot_download(
                settings.RERANKER_MODEL_ID,
                cache_dir=str(cache_dir),
                local_files_only=settings.RERANKER_LOCAL_FILES_ONLY,
            )
            self._model = CrossEncoder(model_dir)
            print(f"  [Reranker] {settings.RERANKER_MODEL_ID} 就绪 (路径: {model_dir})")
        except Exception as e:
            print(f"  [Reranker] 模型加载失败，跳过重排: {e}")
            self._model = False

    def _rerank_sync(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        limit: int,
        text_key: str,
    ) -> list[dict[str, Any]]:
        self._lazy_load()

        if not self._model or self._model is False:
            return candidates[:limit]

        pairs = [(query, _candidate_text(candidate, text_key)) for candidate in candidates]

        try:
            try:
                scores = self._model.predict(
                    pairs,
                    show_progress_bar=False,
                )
            except TypeError:
                scores = self._model.predict(pairs)
        except Exception as e:
            print(f"  [Reranker] 重排失败，使用向量召回顺序: {e}")
            return candidates[:limit]

        reranked = []
        for candidate, score in zip(candidates, scores):
            item = dict(candidate)
            item["rerank_score"] = float(score)
            reranked.append(item)

        reranked.sort(key=lambda item: item.get("rerank_score", 0), reverse=True)
        return reranked[:limit]

    async def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        top_k: int | None = None,
        text_key: str = "document",
    ) -> list[dict[str, Any]]:
        """Return candidates sorted by cross-encoder score."""
        if not candidates:
            return []

        limit = top_k if top_k is not None else len(candidates)
        started_at = time.perf_counter()
        logger.info("[RAG.reranker] start candidates=%d", len(candidates))
        try:
            return await run_model_operation(
                self._rerank_sync,
                query,
                candidates,
                limit,
                text_key,
            )
        finally:
            logger.info(
                "[RAG.reranker] end candidates=%d elapsed=%.2fs",
                len(candidates),
                time.perf_counter() - started_at,
            )


def _candidate_text(candidate: dict[str, Any], text_key: str) -> str:
    text = candidate.get(text_key) or candidate.get("document")
    if text:
        return str(text)

    metadata = candidate.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    pieces = []
    for key in ("name", "category", "cuisine", "tags", "address", "description"):
        value = candidate.get(key, metadata.get(key))
        if value:
            pieces.append(str(value))
    return "。".join(pieces) or str(candidate.get("id", ""))


reranker_service = RerankerService()
