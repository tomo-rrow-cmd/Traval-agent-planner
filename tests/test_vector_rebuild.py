from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.vector import rebuild as rebuild_module


class FakeStore:
    counts: dict[str, int] = {}
    fail_validation = False

    def __init__(self, persist_dir, lock_timeout=0):
        _ = lock_timeout
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True)

    def validate(self):
        if self.fail_validation:
            raise RuntimeError("validation failed")
        return SimpleNamespace(collections=dict(self.counts))

    def search(self, name, sample, n_results=1):
        _ = name, sample, n_results
        return {"ids": [["item-1"]]}

    def close(self):
        pass


@pytest.fixture
def fake_rebuild(monkeypatch):
    async def fake_preflight(_allow_pseudo):
        pass

    async def fake_load_rows(spec):
        return [object()] * FakeStore.counts[spec.name]

    async def fake_build(_store, _spec, rows, _batch_size):
        return [0.1] if rows else None

    monkeypatch.setattr(rebuild_module, "VectorStore", FakeStore)
    monkeypatch.setattr(rebuild_module, "_ensure_real_embedding", fake_preflight)
    monkeypatch.setattr(rebuild_module, "_load_rows", fake_load_rows)
    monkeypatch.setattr(rebuild_module, "_build_collection", fake_build)
    FakeStore.counts = {
        "attractions": 2,
        "restaurants": 1,
        "hotels": 0,
    }
    FakeStore.fail_validation = False


@pytest.mark.asyncio
async def test_rebuild_promotes_staging_and_keeps_backup(tmp_path, fake_rebuild):
    active = tmp_path / "chroma_data"
    active.mkdir()
    (active / "old.marker").write_text("old")

    result = await rebuild_module._rebuild_locked(active, 32, False)

    assert result.active_dir == active
    assert active.is_dir()
    assert not (active / "old.marker").exists()
    assert result.backup_dir is not None
    assert (result.backup_dir / "old.marker").read_text() == "old"
    assert result.counts == FakeStore.counts


@pytest.mark.asyncio
async def test_rebuild_validation_failure_leaves_active_untouched(tmp_path, fake_rebuild):
    active = tmp_path / "chroma_data"
    active.mkdir()
    (active / "old.marker").write_text("old")
    FakeStore.fail_validation = True

    with pytest.raises(RuntimeError, match="validation failed"):
        await rebuild_module._rebuild_locked(active, 32, False)

    assert (active / "old.marker").read_text() == "old"
    assert not list(tmp_path.glob(".chroma_data.rebuild-*"))


@pytest.mark.asyncio
async def test_rebuild_rolls_back_when_promotion_fails(
    monkeypatch,
    tmp_path,
    fake_rebuild,
):
    active = tmp_path / "chroma_data"
    active.mkdir()
    (active / "old.marker").write_text("old")
    original_rename = Path.rename

    def fail_staging_promotion(path, target):
        if path.name.startswith(".chroma_data.rebuild-"):
            raise OSError("promotion failed")
        return original_rename(path, target)

    monkeypatch.setattr(Path, "rename", fail_staging_promotion)

    with pytest.raises(OSError, match="promotion failed"):
        await rebuild_module._rebuild_locked(active, 32, False)

    assert (active / "old.marker").read_text() == "old"


@pytest.mark.asyncio
async def test_rebuild_accepts_empty_collections(tmp_path, fake_rebuild):
    FakeStore.counts = {
        "attractions": 0,
        "restaurants": 0,
        "hotels": 0,
    }

    result = await rebuild_module._rebuild_locked(
        tmp_path / "chroma_data",
        32,
        False,
    )

    assert result.counts == FakeStore.counts
    assert result.active_dir.is_dir()
