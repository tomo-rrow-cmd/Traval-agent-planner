"""方案接口 - 对齐 docs/api/API接口规范文档.md §5"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from app.api.v1.chat import sse_response
from app.dependencies import get_current_user, get_plan_service, get_conversation_service
from app.exceptions import NotFoundException, PlanExportFormatException
from app.schemas.common import BaseResponse, EmptyData, PaginatedData
from app.schemas.plan import (
    PlanCreateRequest,
    PlanExportTask,
    PlanFavoriteResult,
    PlanFromDataRequest,
    PlanModifyRequest,
    PlanRegenerateRequest,
    PlanResponse,
    PlanSaveResult,
    PlanShareRequest,
    PlanShareResult,
    PlanSummary,
)
from app.services.application import TravelPlanService
from app.services.application.conversation_service import ConversationService

router = APIRouter(prefix="/plans", tags=["方案接口"])


def plan_generation_events(plan_id: str = "plan_mock_001") -> list[tuple[str, dict]]:
    """方案生成 SSE 占位事件"""
    return [
        (
            "message",
            {
                "role": "assistant",
                "content": "已收到方案生成请求，正在创建旅行方案。",
                "message_type": "plan_progress",
                "suggestions": [],
            },
        ),
        ("step_start", {"step": "parallel_planning", "label": "正在为您规划行程..."}),
        ("progress", {"percent": 40, "message": "已完成基础行程结构"}),
        ("progress", {"percent": 85, "message": "正在整理预算和天气建议"}),
        ("step_end", {"step": "parallel_planning"}),
        ("done", {"plan_id": plan_id, "redirect_url": f"/plans/{plan_id}"}),
    ]


def plan_confirmation_required_events() -> list[tuple[str, dict]]:
    """未确认时不进入方案生成链路。"""
    return [
        (
            "message",
            {
                "role": "assistant",
                "content": "请先确认旅行参数，确认后我再开始生成完整方案。",
                "message_type": "text",
                "suggestions": ["确认，开始规划", "我想再改一下"],
            },
        ),
        ("done", {"status": "waiting_confirmation"}),
    ]


@router.get("", response_model=BaseResponse[PaginatedData[PlanSummary]])
async def list_plans(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    saved: bool = Query(default=False, description="仅显示用户主动保存的方案"),
    current_user: dict = Depends(get_current_user),
    plan_service: TravelPlanService = Depends(get_plan_service),
):
    """获取方案列表"""
    return BaseResponse(
        data=await plan_service.list_plans(
            user_id=current_user["user_id"],
            page=page,
            page_size=page_size,
            status=status,
            saved_only=saved,
        )
    )


@router.post("")
async def create_plan(
    request: PlanCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    """触发方案生成并返回 SSE 流"""
    _ = current_user
    if not request.confirmed:
        return sse_response(plan_confirmation_required_events())
    return sse_response(plan_generation_events(plan_id=f"plan_{request.session_id}"))


@router.get("/{plan_id}", response_model=BaseResponse[PlanResponse])
async def get_plan(
    plan_id: str,
    current_user: dict = Depends(get_current_user),
    plan_service: TravelPlanService = Depends(get_plan_service),
):
    """获取方案详情"""
    return BaseResponse(
        data=await plan_service.get_plan(
            user_id=current_user["user_id"],
            plan_id=plan_id,
        )
    )


@router.patch("/{plan_id}")
async def modify_plan(
    plan_id: str,
    request: PlanModifyRequest,
    current_user: dict = Depends(get_current_user),
):
    """局部修改方案并返回 SSE 流"""
    _ = current_user, request
    return sse_response(
        [
            ("step_start", {"step": "modifying", "label": "正在调整行程..."}),
            ("progress", {"percent": 50, "message": "已应用契约 MVP 修改占位"}),
            ("step_end", {"step": "modify_complete"}),
            ("done", {"plan_id": plan_id, "updated_sections": ["day_1"]}),
        ]
    )


@router.post("/{plan_id}/generations")
async def regenerate_plan(
    plan_id: str,
    request: PlanRegenerateRequest,
    current_user: dict = Depends(get_current_user),
):
    """重新生成方案并返回 SSE 流"""
    _ = current_user, request
    if not request.confirmed:
        return sse_response(plan_confirmation_required_events())
    return sse_response(plan_generation_events(plan_id=plan_id))


@router.delete("/{plan_id}", response_model=BaseResponse[EmptyData])
async def delete_plan(
    plan_id: str,
    current_user: dict = Depends(get_current_user),
    plan_service: TravelPlanService = Depends(get_plan_service),
):
    """删除方案"""
    await plan_service.delete_plan(
        user_id=current_user["user_id"],
        plan_id=plan_id,
    )
    return BaseResponse(data=EmptyData())


@router.post("/{plan_id}/exports")
async def export_plan(
    plan_id: str,
    http_request: Request,
    format: str = Query(...),
    current_user: dict = Depends(get_current_user),
    plan_service: TravelPlanService = Depends(get_plan_service),
):
    """同步导出 Markdown，或创建 PDF/PNG/DOCX 后台任务。"""
    from app.services.export.exporter import export_plan as do_export
    from app.services.export.task_manager import export_task_manager, schedule_export_task

    if format not in ("md", "docx", "pdf", "image"):
        raise PlanExportFormatException()

    plan_data = None
    try:
        body = await http_request.json()
        if isinstance(body, dict) and isinstance(body.get("plan_data"), dict):
            plan_data = body["plan_data"]
    except Exception:
        pass

    if not plan_data:
        try:
            plan_resp = await plan_service.get_plan(
                user_id=current_user["user_id"],
                plan_id=plan_id,
            )
            plan_data = (
                plan_resp.model_dump()
                if hasattr(plan_resp, "model_dump")
                else plan_resp
            )
        except NotFoundException:
            conv_service = ConversationService()
            run = await conv_service.get_plan_run(plan_id)
            if not run:
                raise NotFoundException("方案不存在")
            plan_data = run.get("summary") or {}
            if run.get("destination"):
                plan_data["destination"] = run["destination"]
            if run.get("days"):
                plan_data["days"] = run["days"]
            plan_data.setdefault("full_data", plan_data.copy())

    plan_title = str(
        plan_data.get("title") or plan_data.get("destination") or plan_id
    ).replace(" ", "_")
    sanitized_title = (
        "".join(char for char in plan_title if char.isalnum() or char in "_-")
        .rstrip("._-")
        or plan_id
    )

    if format == "md":
        content, mime = do_export(plan_data, format)
        ascii_name = "".join(
            char for char in sanitized_title if ord(char) < 128
        ).strip(".") or "export"
        encoded_name = quote(f"{sanitized_title}.md", safe="")
        return Response(
            content=content, media_type=mime,
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{ascii_name}.md"; '
                    f"filename*=UTF-8''{encoded_name}"
                )
            },
        )

    task = export_task_manager.create(
        current_user["user_id"],
        plan_id,
        format,
        title=sanitized_title,
    )
    schedule_export_task(task.task_id, plan_data)
    return BaseResponse(data=PlanExportTask(task_id=task.task_id))


@router.post("/{plan_id}/shares", response_model=BaseResponse[PlanShareResult])
async def share_plan(
    plan_id: str,
    request: PlanShareRequest,
    current_user: dict = Depends(get_current_user),
    plan_service: TravelPlanService = Depends(get_plan_service),
):
    """分享方案"""
    return BaseResponse(
        data=await plan_service.share_plan(
            user_id=current_user["user_id"],
            plan_id=plan_id,
            request=request,
        )
    )


@router.post("/from-data", response_model=BaseResponse[PlanResponse])
async def create_plan_from_data(
    request: PlanFromDataRequest,
    current_user: dict = Depends(get_current_user),
    plan_service: TravelPlanService = Depends(get_plan_service),
):
    """从本地缓存数据创建方案并保存到「我的方案」"""
    return BaseResponse(
        data=await plan_service.create_plan_from_data(
            user_id=current_user["user_id"],
            data=request,
        )
    )


@router.post("/{plan_id}/save", response_model=BaseResponse[PlanSaveResult])
async def save_plan(
    plan_id: str,
    current_user: dict = Depends(get_current_user),
    plan_service: TravelPlanService = Depends(get_plan_service),
):
    """用户主动保存方案到「我的方案」"""
    return BaseResponse(
        data=await plan_service.save_plan(
            user_id=current_user["user_id"],
            plan_id=plan_id,
        )
    )


@router.post("/{plan_id}/favorites", response_model=BaseResponse[PlanFavoriteResult])
async def toggle_favorite(
    plan_id: str,
    current_user: dict = Depends(get_current_user),
    plan_service: TravelPlanService = Depends(get_plan_service),
):
    """收藏/取消收藏方案"""
    return BaseResponse(
        data=await plan_service.toggle_favorite(
            user_id=current_user["user_id"],
            plan_id=plan_id,
        )
    )
