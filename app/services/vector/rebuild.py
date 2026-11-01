"""Build and atomically promote a complete Chroma POI index."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import shutil
from typing import Any
from uuid import uuid4

from filelock import FileLock
from sqlalchemy import select

from app.db.session import async_session_factory
from app.services.vector.embedding import embedding_service
from app.services.vector.poi_index import POI_INDEX_SPECS, CollectionSpec
from app.services.vector.vector_store import (
    VectorStore,
    acquire_vector_lock,
    lock_path_for,
    resolve_persist_dir,
)


@dataclass(frozen=True)
class RebuildResult:
    active_dir: Path
    backup_dir: Path | None
    counts: dict[str, int]


async def _load_rows(spec: CollectionSpec) -> list[Any]:
    query = select(spec.model).order_by(spec.model.city, spec.model.name)
    async with async_session_factory() as db:
        result = await db.execute(query)
        return list(result.scalars().all())


async def _ensure_real_embedding(allow_pseudo: bool) -> None:
    vector = (await embedding_service.embed(["向量模型预检"]))[0]
    model_loaded = getattr(embedding_service, "_model", None)
    if model_loaded is False and not allow_pseudo:
        raise RuntimeError(
            "Embedding 模型未成功加载，已停止重建。"
            "请确保 BAAI/bge-m3 已在本地缓存；"
            "临时测试可加 --allow-pseudo。"
        )
    print(f"  [Preflight] embedding 维度: {len(vector)}")


async def _build_collection(
    store: VectorStore,
    spec: CollectionSpec,
    rows: list[Any],
    batch_size: int,
) -> list[float] | None:
    store.get_or_create_collection(spec.name)
    sample_vector: list[float] | None = None
    total = 0
    for start in range(0, len(rows), batch_size):
        batch = rows[start:start + batch_size]
        documents = [spec.document_builder(item) for item in batch]
        embeddings = await embedding_service.embed(documents)
        if sample_vector is None and embeddings:
            sample_vector = embeddings[0]
        store.upsert(
            spec.name,
            [str(item.id) for item in batch],
            embeddings,
            documents,
            [spec.metadata_builder(item) for item in batch],
        )
        total += len(batch)
        print(f"  [{spec.name}] {total}/{len(rows)}")
    return sample_vector


async def _rebuild_locked(
    active_dir: Path,
    batch_size: int,
    allow_pseudo: bool,
) -> RebuildResult:
    await _ensure_real_embedding(allow_pseudo)

    staging_dir = active_dir.parent / f".{active_dir.name}.rebuild-{uuid4().hex}"
    backup_dir = active_dir.parent / (
        f"{active_dir.name}.backup-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"
    )
    expected_counts: dict[str, int] = {}
    samples: dict[str, list[float]] = {}
    store = VectorStore(staging_dir, lock_timeout=0)

    try:
        for spec in POI_INDEX_SPECS:
            rows = await _load_rows(spec)
            expected_counts[spec.name] = len(rows)
            print(f"\n[{spec.name}] PostgreSQL 读取：{len(rows)} 条")
            sample = await _build_collection(store, spec, rows, batch_size)
            if sample is not None:
                samples[spec.name] = sample

        health = store.validate()
        if health.collections != expected_counts:
            raise RuntimeError(
                "影子索引数量校验失败: "
                f"expected={expected_counts}, actual={health.collections}"
            )
        for name, sample in samples.items():
            result = store.search(name, sample, n_results=1)
            if not result.get("ids") or not result["ids"][0]:
                raise RuntimeError(f"影子索引样例查询失败: {name}")
    except Exception:
        store.close()
        shutil.rmtree(staging_dir, ignore_errors=True)
        lock_path_for(staging_dir).unlink(missing_ok=True)
        raise
    else:
        store.close()
        lock_path_for(staging_dir).unlink(missing_ok=True)

    promoted_backup: Path | None = None
    try:
        if active_dir.exists():
            active_dir.rename(backup_dir)
            promoted_backup = backup_dir
        staging_dir.rename(active_dir)
    except Exception:
        if promoted_backup is not None and not active_dir.exists():
            promoted_backup.rename(active_dir)
        raise

    return RebuildResult(
        active_dir=active_dir,
        backup_dir=promoted_backup,
        counts=expected_counts,
    )


async def rebuild_vector_index(
    persist_dir: str | Path | None = None,
    batch_size: int = 32,
    allow_pseudo: bool = False,
    maintenance_lock: FileLock | None = None,
) -> RebuildResult:
    """Build all POI collections off-path and atomically promote them."""
    active_dir = resolve_persist_dir(persist_dir)
    if maintenance_lock is not None:
        if not maintenance_lock.is_locked:
            raise RuntimeError("maintenance_lock 必须已获取")
        return await _rebuild_locked(active_dir, batch_size, allow_pseudo)

    with acquire_vector_lock(active_dir) as acquired_lock:
        return await rebuild_vector_index(
            active_dir,
            batch_size=batch_size,
            allow_pseudo=allow_pseudo,
            maintenance_lock=acquired_lock,
        )
