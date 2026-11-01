"""进程内方案导出任务管理。"""

from __future__ import annotations

import asyncio
import shutil
import tempfile
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.exceptions import BadRequestException, NotFoundException
from app.schemas.common import TaskStatus
from app.services.export.exporter import export_plan


TASK_TTL = timedelta(hours=1)
TASK_DIR = Path(tempfile.gettempdir()) / "ai-travel-planner-exports"
# 限制并发导出任务数（PDF/DOCX 渲染为 CPU/内存密集型）
EXPORT_SEMAPHORE = asyncio.Semaphore(2)


@dataclass
class ExportTask:
    task_id: str
    user_id: str
    plan_id: str
    format: str
    title: str = ""  # 方案标题，用于文件名
    status: str = "processing"
    progress: int = 0
    message: str = "等待生成"
    file_path: Path | None = None
    mime_type: str | None = None
    expires_at: datetime | None = None
    error: dict | None = None
    extension: str | None = None  # 实际文件扩展名


class ExportTaskManager:
    def __init__(self) -> None:
        self._tasks: dict[str, ExportTask] = {}
        self._lock = threading.RLock()

    def create(self, user_id: str, plan_id: str, format: str, title: str = "") -> ExportTask:
        self.cleanup()
        task = ExportTask(
            task_id=f"task_export_{uuid.uuid4().hex}",
            user_id=user_id,
            plan_id=plan_id,
            format=format,
            title=title,
        )
        with self._lock:
            self._tasks[task.task_id] = task
        return task

    def run(self, task_id: str, plan: dict) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return
            task.progress = 20
            task.message = "正在生成导出文件"
        try:
            content, mime_type = export_plan(plan, task.format)
            TASK_DIR.mkdir(parents=True, exist_ok=True)
            if task.format == "pdf":
                if "application/pdf" not in mime_type or not content.startswith(b"%PDF-"):
                    raise RuntimeError("PDF export returned an invalid file")
                extension = "pdf"
            elif "html" in mime_type:
                extension = "html"
            elif "png" in mime_type:
                extension = "png"
            else:
                extension = task.format
            path = TASK_DIR / f"{task.task_id}.{extension}"
            path.write_bytes(content)
            with self._lock:
                task.file_path = path
                task.mime_type = mime_type
                task.status = "completed"
                task.progress = 100
                task.message = "导出完成"
                task.expires_at = datetime.now(timezone.utc) + TASK_TTL
                task.extension = extension
        except Exception:
            with self._lock:
                task.status = "failed"
                task.progress = 100
                task.message = "方案导出失败，请稍后重试"
                task.error = {"code": 40005, "message": task.message}
                task.expires_at = datetime.now(timezone.utc) + TASK_TTL

    def get(self, task_id: str, user_id: str) -> ExportTask:
        self.cleanup()
        with self._lock:
            task = self._tasks.get(task_id)
        if task is None or task.user_id != user_id:
            raise NotFoundException("Export task not found")
        return task

    def status(self, task_id: str, user_id: str) -> TaskStatus:
        task = self.get(task_id, user_id)
        return TaskStatus(
            task_id=task.task_id,
            type="plan_export",
            status=task.status,
            progress=task.progress,
            message=task.message,
            download_url=(f"/api/v1/tasks/{task.task_id}/download"
                          if task.status == "completed" else None),
            expires_at=task.expires_at,
            error=task.error,
        )

    def download(self, task_id: str, user_id: str) -> ExportTask:
        task = self.get(task_id, user_id)
        if task.status == "processing":
            raise BadRequestException("Export task is still processing")
        if task.status == "failed" or task.file_path is None or not task.file_path.exists():
            raise NotFoundException("Export file not available")
        return task

    def cleanup(self) -> None:
        now = datetime.now(timezone.utc)
        with self._lock:
            expired = [
                task_id for task_id, task in self._tasks.items()
                if task.expires_at is not None and task.expires_at <= now
            ]
            for task_id in expired:
                task = self._tasks.pop(task_id)
                if task.file_path:
                    task.file_path.unlink(missing_ok=True)

    def clear(self) -> None:
        with self._lock:
            self._tasks.clear()
        shutil.rmtree(TASK_DIR, ignore_errors=True)


export_task_manager = ExportTaskManager()
_running_tasks: set[asyncio.Task] = set()


async def run_export_task(task_id: str, plan: dict) -> None:
    """在线程中执行文件渲染（受 EXPORT_SEMAPHORE 限流）。"""
    async with EXPORT_SEMAPHORE:
        await asyncio.to_thread(export_task_manager.run, task_id, plan)


def schedule_export_task(task_id: str, plan: dict) -> None:
    """调度并持有后台任务引用直至完成。"""
    task = asyncio.create_task(run_export_task(task_id, plan))
    _running_tasks.add(task)
    task.add_done_callback(_running_tasks.discard)
