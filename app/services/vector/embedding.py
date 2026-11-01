"""
Embedding 服务 — BGE 语义模型（真实 RAG）

模型：BAAI/bge-m3（1024维，多语言/中文表现更稳）
通过 ModelScope 下载和管理，首次下载后从本地缓存加载。
"""

import logging
import time
from pathlib import Path
from typing import Optional

from app.config import settings
from app.services.vector.runtime import run_model_operation


logger = logging.getLogger(__name__)


class EmbeddingService:
    """中文语义向量化服务（BGE 模型 + 查询缓存）"""

    def __init__(self):
        self._model: Optional[object] = None
        self._cache: dict[str, list[float]] = {}  # 查询缓存

    def _lazy_load(self):
        """延迟加载模型 — ModelScope snapshot → SentenceTransformer。"""
        if self._model is not None:
            return

        cache_dir = Path(settings.EMBEDDING_MODEL_CACHE_DIR)
        cache_dir.mkdir(parents=True, exist_ok=True)
        model_id = settings.EMBEDDING_MODEL_ID

        try:
            from modelscope import snapshot_download
            from sentence_transformers import SentenceTransformer

            model_dir = snapshot_download(
                model_id,
                cache_dir=str(cache_dir),
                local_files_only=settings.EMBEDDING_LOCAL_FILES_ONLY,
            )
            self._model = SentenceTransformer(model_dir)
            dim = self._model.get_embedding_dimension()
            print(f"  [Embedding] {model_id} 就绪 (ModelScope, 维度: {dim})")
        except Exception as e:
            print(f"  [Embedding] 模型加载失败: {e}")
            self._model = False

    def _embed_sync(self, texts: list[str]) -> list[list[float]]:
        self._lazy_load()

        if self._model and self._model is not False:
            embeddings = self._model.encode(
                texts,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return [e.tolist() for e in embeddings]
        return [_pseudo_embed(t, settings.EMBEDDING_DIM) for t in texts]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """文本列表 → 向量列表"""
        started_at = time.perf_counter()
        logger.info("[RAG.embedding] start batch_size=%d", len(texts))
        try:
            return await run_model_operation(self._embed_sync, texts)
        finally:
            logger.info(
                "[RAG.embedding] end batch_size=%d elapsed=%.2fs",
                len(texts),
                time.perf_counter() - started_at,
            )

    async def embed_query(self, text: str) -> list[float]:
        """单条查询 → 向量（缓存命中则跳过计算）"""
        if text in self._cache:
            return self._cache[text]
        results = await self.embed([text])
        vec = results[0]
        if len(self._cache) > 500:
            self._cache.pop(next(iter(self._cache)))  # 淘汰最旧
        self._cache[text] = vec
        return vec


def _pseudo_embed(text: str, dim: int = 1024) -> list[float]:
    """降级伪 embedding"""
    import hashlib, struct
    vec = [0.0] * dim
    for i, ch in enumerate(text):
        h = hashlib.sha256(f"{i}:{ch}".encode()).digest()
        for j in range(0, len(h), 4):
            idx = struct.unpack("<I", h[j:j + 4])[0] % dim
            vec[idx] += 0.01
    norm = sum(v * v for v in vec) ** 0.5
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


embedding_service = EmbeddingService()
