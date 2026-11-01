import os
from pathlib import Path
import subprocess
import sys

import pytest

from app.services.vector.vector_store import (
    VectorStore,
    VectorStoreBusyError,
    VectorStoreCorruptError,
    acquire_vector_lock,
    resolve_persist_dir,
)


def test_vector_store_resolves_relative_path_from_project_root(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "app.services.vector.vector_store.PROJECT_ROOT",
        tmp_path,
    )

    assert resolve_persist_dir("vectors") == (tmp_path / "vectors").resolve()


def test_vector_store_rejects_second_process_lease(tmp_path):
    persist_dir = tmp_path / "chroma"

    with acquire_vector_lock(persist_dir, timeout=0):
        store = VectorStore(persist_dir, lock_timeout=0)
        with pytest.raises(VectorStoreBusyError):
            store.open()


def test_vector_store_close_releases_lease(tmp_path):
    persist_dir = tmp_path / "chroma"
    store = VectorStore(persist_dir, lock_timeout=0)
    store.open()
    store.close()

    with acquire_vector_lock(persist_dir, timeout=0):
        pass


def test_vector_store_rejects_lease_from_second_process(tmp_path):
    persist_dir = tmp_path / "chroma"
    project_root = Path(__file__).resolve().parents[1]
    code = (
        "from app.services.vector.vector_store import VectorStore, VectorStoreBusyError; "
        f"store=VectorStore({str(persist_dir)!r}, lock_timeout=0); "
        "\ntry: store.open()\n"
        "except VectorStoreBusyError: raise SystemExit(23)\n"
        "raise SystemExit(0)"
    )
    environment = dict(os.environ, PYTHONPATH=str(project_root))

    with acquire_vector_lock(persist_dir, timeout=0):
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=project_root,
            env=environment,
            check=False,
            timeout=10,
        )

    assert result.returncode == 23


def test_vector_store_empty_index_is_degraded_not_corrupt(tmp_path):
    store = VectorStore(tmp_path / "chroma", lock_timeout=0)
    try:
        health = store.validate()
    finally:
        store.close()

    assert health.status == "empty"
    assert health.collections == {}


def test_vector_store_reopens_and_queries_all_poi_collections(tmp_path):
    persist_dir = tmp_path / "chroma"
    first = VectorStore(persist_dir, lock_timeout=0)
    for index, name in enumerate(("attractions", "restaurants", "hotels")):
        first.upsert(
            name,
            [f"item-{index}"],
            [[1.0, float(index)]],
            [name],
            [{"city": "北京", "name": name}],
        )
    assert first.validate().collections == {
        "attractions": 1,
        "restaurants": 1,
        "hotels": 1,
    }
    first.close()

    second = VectorStore(persist_dir, lock_timeout=0)
    try:
        health = second.validate()
        for name in health.collections:
            result = second.search(name, [1.0, 0.0], n_results=1)
            assert result["ids"][0]
    finally:
        second.close()


def test_vector_store_wraps_collection_read_failure(monkeypatch, tmp_path):
    class BrokenCollection:
        def count(self):
            raise RuntimeError("broken hnsw")

    class BrokenClient:
        def list_collections(self):
            return [type("Collection", (), {"name": "attractions"})()]

        def get_collection(self, name):
            assert name == "attractions"
            return BrokenCollection()

        def close(self):
            pass

    monkeypatch.setattr(
        "app.services.vector.vector_store._create_persistent_client",
        lambda _path: BrokenClient(),
    )
    store = VectorStore(tmp_path / "chroma", lock_timeout=0)
    try:
        with pytest.raises(VectorStoreCorruptError, match="rebuild_vectors.py"):
            store.validate()
        assert store.health.status == "unhealthy"
    finally:
        store.close()


def test_delete_collection_error_is_not_swallowed(tmp_path):
    class BrokenClient:
        def delete_collection(self, name):
            raise RuntimeError(f"cannot delete {name}")

        def close(self):
            pass

    store = VectorStore(tmp_path / "chroma", lock_timeout=0)
    store._client = BrokenClient()

    with pytest.raises(RuntimeError, match="cannot delete attractions"):
        store.delete_collection("attractions")
