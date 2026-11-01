"""进程内导出任务测试。"""

from datetime import datetime, timedelta, timezone

import pytest

from app.exceptions import NotFoundException
from app.services.export import task_manager as task_module


@pytest.fixture(autouse=True)
def clean_tasks():
    task_module.export_task_manager.clear()
    yield
    task_module.export_task_manager.clear()


def test_export_task_completes_and_exposes_download(monkeypatch):
    monkeypatch.setattr(
        task_module, "export_plan",
        lambda plan, format: (b"%PDF-test", "application/pdf"),
    )
    task = task_module.export_task_manager.create("user-1", "plan-1", "pdf")

    task_module.export_task_manager.run(task.task_id, {"destination": "杭州"})

    status = task_module.export_task_manager.status(task.task_id, "user-1")
    download = task_module.export_task_manager.download(task.task_id, "user-1")
    assert status.status == "completed"
    assert status.download_url == f"/api/v1/tasks/{task.task_id}/download"
    assert download.file_path.read_bytes().startswith(b"%PDF")


def test_export_task_hides_other_users_tasks():
    task = task_module.export_task_manager.create("user-1", "plan-1", "pdf")

    with pytest.raises(NotFoundException):
        task_module.export_task_manager.status(task.task_id, "user-2")


def test_export_task_cleanup_removes_expired_file(monkeypatch):
    monkeypatch.setattr(task_module, "export_plan", lambda plan, format: (b"file", "image/png"))
    task = task_module.export_task_manager.create("user-1", "plan-1", "image")
    task_module.export_task_manager.run(task.task_id, {})
    path = task.file_path
    task.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)

    task_module.export_task_manager.cleanup()

    assert path is not None and not path.exists()
    with pytest.raises(NotFoundException):
        task_module.export_task_manager.get(task.task_id, "user-1")


def test_export_task_run_failure_sets_failed_status(monkeypatch):
    """异常路径: export_plan 失败 → task.status = 'failed'"""
    def failing_export(plan, format):
        raise RuntimeError("export failed")

    monkeypatch.setattr(task_module, "export_plan", failing_export)
    task = task_module.export_task_manager.create("user-1", "plan-1", "md")

    # 不应该抛出异常
    task_module.export_task_manager.run(task.task_id, {"destination": "test"})

    status = task_module.export_task_manager.status(task.task_id, "user-1")
    assert status.status == "failed"
    assert status.message == "方案导出失败，请稍后重试"
    assert status.error is not None
    assert status.error["code"] == 40005


def test_pdf_export_rejects_html_fallback(monkeypatch):
    monkeypatch.setattr(
        task_module,
        "export_plan",
        lambda plan, format: (b"<!DOCTYPE html>", "text/html; charset=utf-8"),
    )
    task = task_module.export_task_manager.create("user-1", "plan-1", "pdf")

    task_module.export_task_manager.run(task.task_id, {"destination": "test"})

    status = task_module.export_task_manager.status(task.task_id, "user-1")
    assert status.status == "failed"
    assert status.download_url is None


def test_export_task_download_while_processing_raises(monkeypatch):
    """下载处理中的任务 → BadRequestException"""
    task = task_module.export_task_manager.create("user-1", "plan-1", "md")
    # 不调用 run()，状态保持 "processing"

    from app.exceptions import BadRequestException
    with pytest.raises(BadRequestException, match="still processing"):
        task_module.export_task_manager.download(task.task_id, "user-1")


def test_export_task_download_failed_raises(monkeypatch):
    """下载失败的任务 → NotFoundException"""
    task = task_module.export_task_manager.create("user-1", "plan-1", "md")
    task.status = "failed"
    task.file_path = None

    with pytest.raises(NotFoundException):
        task_module.export_task_manager.download(task.task_id, "user-1")
