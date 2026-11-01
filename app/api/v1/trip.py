"""
V2.0 Trip API — 行程执行 / 签到 / 花费 / 调整 / 提醒
"""

import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.dependencies import get_current_user, get_trip_service
from app.schemas.common import BaseResponse, EmptyData, PaginatedData
from app.schemas.trip import (
    TripStartRequest, TripStatusUpdateRequest, TripResponse, TripProgressResponse,
    CheckinCreateRequest, CheckinResponse,
    ExpenseCreateRequest, ExpenseResponse,
    AdjustmentCreateRequest, AdjustmentResponse,
    PhotoAnnotateRequest,
)
from app.services.application.trip_service import TripService

router = APIRouter(prefix="/trips", tags=["Trip Execution"])


# ==================== Trip CRUD ====================

@router.post("", response_model=BaseResponse[TripResponse])
async def start_trip(
    body: TripStartRequest,
    current_user: dict = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
    http_request: Request = None,
):
    """从方案创建行程执行实例 — "开始旅行" """
    try:
        # 从原始请求 body 中提取 plan_data（Pydantic 对复杂 dict 解析有限制）
        plan_data = None
        if http_request is not None:
            try:
                raw_body = await http_request.json()
                plan_data = raw_body.get("plan_data")
            except Exception:
                pass

        result = await service.start_trip(
            user_id=current_user["user_id"],
            plan_id=body.plan_id,
            plan_data=plan_data,
        )
        return BaseResponse(data=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=BaseResponse[PaginatedData[TripResponse]])
async def list_trips(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
):
    """我的行程列表"""
    return BaseResponse(data=await service.list_trips(
        user_id=current_user["user_id"], status=status, page=page, page_size=page_size))


@router.get("/{trip_id}", response_model=BaseResponse[TripResponse])
async def get_trip(
    trip_id: str,
    current_user: dict = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
):
    """行程执行详情"""
    result = await service.get_trip(trip_id, current_user["user_id"])
    return BaseResponse(data=result)


@router.patch("/{trip_id}", response_model=BaseResponse[TripResponse])
async def update_trip_status(
    trip_id: str,
    request: TripStatusUpdateRequest,
    current_user: dict = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
):
    """更新行程状态: 暂停/继续/完成/放弃"""
    result = await service.update_status(trip_id, current_user["user_id"], request.status)
    return BaseResponse(data=result)


@router.post("/{trip_id}/advance-day", response_model=BaseResponse[TripResponse])
async def advance_day(
    trip_id: str,
    current_user: dict = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
):
    """推进到下一日"""
    try:
        result = await service.advance_day(trip_id, current_user["user_id"])
        return BaseResponse(data=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{trip_id}/progress", response_model=BaseResponse[TripProgressResponse])
async def get_progress(
    trip_id: str,
    current_user: dict = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
):
    """实时进度"""
    result = await service.get_progress(trip_id, current_user["user_id"])
    return BaseResponse(data=result)


# ==================== Checkins ====================

@router.post("/{trip_id}/checkins", response_model=BaseResponse[CheckinResponse])
async def checkin(
    trip_id: str,
    request: CheckinCreateRequest,
    current_user: dict = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
):
    """签到"""
    try:
        result = await service.checkin(
            trip_id=trip_id, user_id=current_user["user_id"],
            poi_type=request.poi_type, poi_name=request.poi_name,
            poi_id=request.poi_id, lat=request.lat, lng=request.lng,
            photos=request.photos or [],
            source_day=request.source_day,
            planned_at=request.planned_at, actual_at=request.actual_at,
            planned_cost=request.planned_cost, actual_cost=request.actual_cost,
            rating=request.rating, note=request.note,
        )
        return BaseResponse(data=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{trip_id}/checkins", response_model=BaseResponse[PaginatedData[CheckinResponse]])
async def list_checkins(
    trip_id: str,
    day: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
):
    """签到记录列表"""
    return BaseResponse(data=await service.list_checkins(
        trip_id=trip_id, day=day, page=page, page_size=page_size))


# ==================== Expenses ====================

@router.post("/{trip_id}/expenses", response_model=BaseResponse[ExpenseResponse])
async def add_expense(
    trip_id: str,
    request: ExpenseCreateRequest,
    current_user: dict = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
):
    """记录花费"""
    result = await service.add_expense(
        trip_id=trip_id, amount=request.amount, category=request.category,
        planned_amount=request.planned_amount, note=request.note,
        spent_at=request.spent_at, checkin_id=request.checkin_id,
    )
    return BaseResponse(data=result)


@router.get("/{trip_id}/expenses", response_model=BaseResponse[list[ExpenseResponse]])
async def list_expenses(
    trip_id: str,
    category: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
):
    """花费明细"""
    return BaseResponse(data=await service.list_expenses(trip_id, category))


# ==================== Adjustments ====================

@router.post("/{trip_id}/adjustments/detect",
             response_model=BaseResponse[AdjustmentResponse])
async def detect_anomalies(
    trip_id: str,
    request: AdjustmentCreateRequest,
    current_user: dict = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
):
    """触发异常检测 + 生成调整"""
    from app.agents.adjust_agent import AdjustAgent
    from app.services.llm.deepseek import DeepSeekLLM

    agent = AdjustAgent(DeepSeekLLM())
    result = await agent.run({
        "trigger_type": request.trigger_type,
        "trigger_detail": request.trigger_detail or {},
        "daily_plan": request.daily_plan,
        "preferences": request.preferences,
        "destination": request.destination,
    })

    adj = await service.create_adjustment(
        trip_id=trip_id, trigger_type=request.trigger_type,
        trigger_detail=result.get("trigger_detail"),
        original_plan=result.get("original_plan"),
        adjusted_plan=result.get("adjusted_plan"),
        reason=result.get("reason", ""),
    )
    return BaseResponse(data=adj)


@router.get("/{trip_id}/adjustments",
            response_model=BaseResponse[PaginatedData[AdjustmentResponse]])
async def list_adjustments(
    trip_id: str,
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
):
    """调整历史"""
    return BaseResponse(data=await service.list_adjustments(
        trip_id=trip_id, status=status, page=page, page_size=page_size))


@router.post("/{trip_id}/adjustments/{adj_id}/accept",
             response_model=BaseResponse[AdjustmentResponse])
async def accept_adjustment(
    trip_id: str,
    adj_id: str,
    current_user: dict = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
):
    """接受调整"""
    result = await service.accept_adjustment(adj_id, trip_id)
    return BaseResponse(data=result)


@router.post("/{trip_id}/adjustments/{adj_id}/reject",
             response_model=BaseResponse[AdjustmentResponse])
async def reject_adjustment(
    trip_id: str,
    adj_id: str,
    current_user: dict = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
):
    """拒绝调整"""
    result = await service.reject_adjustment(adj_id, trip_id)
    return BaseResponse(data=result)


@router.post("/{trip_id}/adjustments/{adj_id}/apply",
             response_model=BaseResponse[AdjustmentResponse])
async def apply_adjustment(
    trip_id: str,
    adj_id: str,
    current_user: dict = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
):
    """应用调整"""
    result = await service.apply_adjustment(adj_id, trip_id)
    return BaseResponse(data=result)


# ==================== Reminder ====================

@router.get("/{trip_id}/reminder",
            response_model=BaseResponse[dict])
async def get_reminder(
    trip_id: str,
    current_user: dict = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
):
    """生成次日提醒"""
    from app.agents.trip_agent import build_trip_reminder

    try:
        reminder_context = await service.get_reminder_context(
            trip_id, current_user["user_id"],
        )
    except ValueError:
        return BaseResponse(data={"error": "Trip not found"})

    reminder = build_trip_reminder(reminder_context)
    return BaseResponse(data=reminder)


# ==================== Photos ====================

@router.post("/{trip_id}/photos/annotate",
             response_model=BaseResponse[dict])
async def annotate_photos(
    trip_id: str,
    request: PhotoAnnotateRequest,
    current_user: dict = Depends(get_current_user),
):
    """AI 照片标注"""
    _ = current_user, trip_id
    from app.agents.travelogue_agent import TravelogueAgent
    from app.services.llm.deepseek import DeepSeekLLM

    agent = TravelogueAgent(DeepSeekLLM())
    result = await agent.annotate_photos({"checkin": request.checkin})
    return BaseResponse(data=result)
