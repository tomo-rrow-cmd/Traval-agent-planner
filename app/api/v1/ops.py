"""运维与任务接口"""

from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.dependencies import get_current_user
from app.schemas.common import BaseResponse, HealthData, TaskStatus
from app.services.vector.vector_store import vector_store

router = APIRouter(tags=["运维与任务接口"])


@router.get("/health", response_model=BaseResponse[HealthData])
async def health_check():
    """健康检查"""
    chroma_status = vector_store.health.status
    return BaseResponse(
        data=HealthData(
            status="healthy" if chroma_status == "healthy" else "degraded",
            version="1.0.0",
            uptime_seconds=0,
            dependencies={
                "postgresql": "not_checked",
                "redis": "not_checked",
                "llm_service": "not_checked",
                "chroma": chroma_status,
            },
        )
    )


@router.get("/tasks/{task_id}", response_model=BaseResponse[TaskStatus])
async def get_task_status(
    task_id: str,
    current_user: dict = Depends(get_current_user),
):
    """查询当前用户的异步导出任务。"""
    from app.services.export.task_manager import export_task_manager

    return BaseResponse(data=export_task_manager.status(task_id, current_user["user_id"]))


@router.get("/tasks/{task_id}/download")
async def download_task(
    task_id: str,
    current_user: dict = Depends(get_current_user),
):
    """下载已完成且未过期的导出文件。"""
    from app.services.export.task_manager import export_task_manager

    task = export_task_manager.download(task_id, current_user["user_id"])
    extension = task.extension or "pdf"
    filename = task.title or task.plan_id
    ascii_name = "".join(c for c in filename if ord(c) < 128).strip(".") or "export"
    encoded = quote(f"{filename}.{extension}", safe="")
    return Response(
        content=task.file_path.read_bytes(),
        media_type=task.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{ascii_name}.{extension}"; filename*=UTF-8\'\'{encoded}',
        },
    )
