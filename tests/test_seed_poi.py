from contextlib import contextmanager

import pytest

from scripts import seed_poi


@pytest.mark.asyncio
async def test_seed_city_holds_maintenance_lock_through_rebuild(monkeypatch):
    events = []
    lock = type("Lock", (), {"is_locked": True})()

    @contextmanager
    def fake_acquire_lock():
        events.append("lock_acquired")
        try:
            yield lock
        finally:
            events.append("lock_released")

    async def fake_fetch(_city, _amap):
        assert events == ["lock_acquired"]
        return []

    async def fake_upsert(*_args):
        events.append("postgres_updated")
        return 0

    async def fake_rebuild(**kwargs):
        assert kwargs["maintenance_lock"] is lock
        events.append("index_rebuilt")
        return type(
            "Result",
            (),
            {"counts": {}, "backup_dir": None},
        )()

    monkeypatch.setattr(seed_poi.settings, "AMAP_API_KEY", "configured")
    monkeypatch.setattr(seed_poi, "acquire_vector_lock", fake_acquire_lock)
    monkeypatch.setattr(seed_poi, "AmapService", object)
    monkeypatch.setattr(seed_poi, "fetch_attractions", fake_fetch)
    monkeypatch.setattr(seed_poi, "fetch_restaurants", fake_fetch)
    monkeypatch.setattr(seed_poi, "fetch_hotels", fake_fetch)
    monkeypatch.setattr(seed_poi, "_upsert_pois", fake_upsert)
    monkeypatch.setattr(seed_poi, "rebuild_vector_index", fake_rebuild)

    await seed_poi.seed_city("北京")

    assert events == [
        "lock_acquired",
        "postgres_updated",
        "postgres_updated",
        "postgres_updated",
        "index_rebuilt",
        "lock_released",
    ]
