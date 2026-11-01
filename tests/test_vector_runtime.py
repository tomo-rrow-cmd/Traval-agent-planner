import asyncio
import threading
import time

import pytest

from app.services.vector.embedding import EmbeddingService
from app.services.vector.runtime import run_model_operation


@pytest.mark.asyncio
async def test_model_operations_are_serialized_without_blocking_event_loop():
    state_lock = threading.Lock()
    active = 0
    max_active = 0

    def slow_operation(value: str) -> str:
        nonlocal active, max_active
        with state_lock:
            active += 1
            max_active = max(max_active, active)
        time.sleep(0.05)
        with state_lock:
            active -= 1
        return value

    tasks = [
        asyncio.create_task(run_model_operation(slow_operation, value))
        for value in ("embedding", "reranker", "embedding-2")
    ]

    heartbeat_started_at = time.perf_counter()
    await asyncio.wait_for(asyncio.sleep(0.01), timeout=0.05)
    assert time.perf_counter() - heartbeat_started_at < 0.04
    assert await asyncio.gather(*tasks) == ["embedding", "reranker", "embedding-2"]
    assert max_active == 1


@pytest.mark.asyncio
async def test_embedding_query_uses_cache():
    class FakeEmbedding:
        def __init__(self, values):
            self._values = values

        def tolist(self):
            return self._values

    class FakeModel:
        def __init__(self):
            self.calls = 0

        def encode(self, texts, **kwargs):
            self.calls += 1
            return [FakeEmbedding([float(len(text))]) for text in texts]

    service = EmbeddingService()
    model = FakeModel()
    service._model = model

    first = await service.embed_query("北京")
    second = await service.embed_query("北京")

    assert first == [2.0]
    assert second == first
    assert model.calls == 1


@pytest.mark.asyncio
async def test_embedding_falls_back_when_model_load_fails(monkeypatch):
    service = EmbeddingService()

    def fail_load():
        service._model = False

    monkeypatch.setattr(service, "_lazy_load", fail_load)

    result = await service.embed(["fallback"])

    assert len(result) == 1
    assert len(result[0]) > 0
