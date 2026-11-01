"""美团酒旅 CLI 配置同步测试"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.third_party import meituan as meituan_module
from app.services.third_party.meituan import MeituanTravel, _terminate_process


def test_sync_config_from_env_creates_mttravel_config(tmp_path):
    service = MeituanTravel()
    config_path = tmp_path / "meituan-travel" / "config.json"
    service.CONFIG_PATH = str(config_path)

    changed = service.sync_config_from_env("token-123")

    assert changed is True
    assert json.loads(config_path.read_text(encoding="utf-8")) == {"key": "token-123"}


def test_sync_config_from_env_preserves_existing_fields(tmp_path):
    service = MeituanTravel()
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"key": "old-token", "channel": "official"}),
        encoding="utf-8",
    )
    service.CONFIG_PATH = str(config_path)

    changed = service.sync_config_from_env("new-token")

    assert changed is True
    assert json.loads(config_path.read_text(encoding="utf-8")) == {
        "key": "new-token",
        "channel": "official",
    }


def test_sync_config_from_env_skips_empty_token(tmp_path):
    service = MeituanTravel()
    config_path = tmp_path / "config.json"
    service.CONFIG_PATH = str(config_path)

    changed = service.sync_config_from_env("")

    assert changed is False
    assert not config_path.exists()


@pytest.mark.asyncio
async def test_query_returns_success(monkeypatch):
    service = MeituanTravel()
    monkeypatch.setattr(MeituanTravel, "available", property(lambda self: True))
    monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/mttravel")

    proc = MagicMock()
    proc.returncode = 0
    proc.communicate = AsyncMock(return_value=("酒店结果".encode(), b""))
    create_process = AsyncMock(return_value=proc)
    monkeypatch.setattr(meituan_module.asyncio, "create_subprocess_exec", create_process)

    result = await service.query("北京", "推荐酒店")

    assert result["success"] is True
    assert result["text"] == "酒店结果"


@pytest.mark.asyncio
async def test_query_timeout_terminates_and_reaps_process(monkeypatch):
    service = MeituanTravel()
    monkeypatch.setattr(MeituanTravel, "available", property(lambda self: True))
    monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/mttravel")

    proc = MagicMock()
    proc.returncode = None
    proc.communicate = AsyncMock()
    proc.wait = AsyncMock()

    async def communicate_forever():
        await asyncio.Event().wait()

    async def wait_after_terminate():
        proc.returncode = -15
        return proc.returncode

    proc.communicate.side_effect = communicate_forever
    proc.wait.side_effect = wait_after_terminate
    monkeypatch.setattr(
        meituan_module.asyncio,
        "create_subprocess_exec",
        AsyncMock(return_value=proc),
    )

    result = await service.query("北京", "推荐酒店", timeout=0.01)

    assert result["error"] == "timeout"
    proc.terminate.assert_called_once_with()
    proc.wait.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_query_cancellation_terminates_process(monkeypatch):
    service = MeituanTravel()
    monkeypatch.setattr(MeituanTravel, "available", property(lambda self: True))
    monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/mttravel")

    started = asyncio.Event()
    proc = MagicMock()
    proc.returncode = None
    proc.communicate = AsyncMock()
    proc.wait = AsyncMock()

    async def communicate_forever():
        started.set()
        await asyncio.Event().wait()

    async def wait_after_terminate():
        proc.returncode = -15
        return proc.returncode

    proc.communicate.side_effect = communicate_forever
    proc.wait.side_effect = wait_after_terminate
    monkeypatch.setattr(
        meituan_module.asyncio,
        "create_subprocess_exec",
        AsyncMock(return_value=proc),
    )

    task = asyncio.create_task(service.query("北京", "推荐酒店"))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    proc.terminate.assert_called_once_with()
    proc.wait.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_terminate_process_kills_after_graceful_timeout():
    proc = MagicMock()
    proc.returncode = None
    wait_calls = 0

    async def wait_for_exit():
        nonlocal wait_calls
        wait_calls += 1
        if wait_calls == 1:
            await asyncio.Event().wait()
        proc.returncode = -9
        return proc.returncode

    proc.wait = AsyncMock(side_effect=wait_for_exit)

    await _terminate_process(proc, graceful_timeout=0.01)

    proc.terminate.assert_called_once_with()
    proc.kill.assert_called_once_with()
    assert proc.wait.await_count == 2
