"""
V2.0 Travelogue API — 游记 / 社交素材 / 分享
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_current_user, get_travelogue_service, get_trip_service
from app.schemas.common import BaseResponse, EmptyData, PaginatedData
from app.schemas.travelogue import (
    TravelogueGenerateRequest, TravelogueUpdateRequest, TravelogueResponse,
    MaterialGenerateRequest, MaterialResponse, MaterialFavoriteRequest,
    RegenerateSectionRequest,
)
from app.schemas.trip import ShareCreateRequest, ShareResponse
from app.services.application.trip_service import TripService
from app.services.application.travelogue_service import TravelogueService

router = APIRouter(prefix="/travelogues", tags=["Travelogue"])


# ==================== Travelogue CRUD ====================

@router.post("", response_model=BaseResponse[TravelogueResponse])
async def generate_travelogue(
    request: TravelogueGenerateRequest,
    current_user: dict = Depends(get_current_user),
    travelogue_service: TravelogueService = Depends(get_travelogue_service),
    trip_service: TripService = Depends(get_trip_service),
):
    """生成或重新生成整趟旅行的主游记。"""
    from app.agents.travelogue_agent import TravelogueAgent
    from app.services.llm.deepseek import DeepSeekLLM

    try:
        trip_info = await trip_service.get_travelogue_context(
            request.trip_id, current_user["user_id"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    existing = await travelogue_service.get_by_trip(request.trip_id)
    if existing and existing["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="无权操作")
    if existing and not request.regenerate:
        return BaseResponse(data=existing)
    if existing and existing["status"] != "draft":
        raise HTTPException(status_code=409, detail="已发布游记不能自动覆盖")

    # AI 生成
    agent = TravelogueAgent(DeepSeekLLM())
    result = await agent.generate({
        "checkins": trip_info["checkins"],
        "style": request.style,
        "trip_info": trip_info,
    })

    payload = dict(
        title=result.get("title"), content=result.get("content"),
        cover_url=result.get("cover_url"), photos=result.get("photos", []),
        style=result.get("style", request.style),
        total_days=result.get("total_days"), total_pois=result.get("total_pois"),
        total_cost=result.get("total_cost"), total_photos=result.get("total_photos"),
    )
    if existing:
        travelogue = await travelogue_service.update(
            existing["id"], user_id=current_user["user_id"], **payload,
        )
    else:
        travelogue = await travelogue_service.create(
            trip_id=request.trip_id, user_id=current_user["user_id"], **payload,
        )
    return BaseResponse(data=travelogue)


@router.get("", response_model=BaseResponse[PaginatedData[TravelogueResponse]])
async def list_travelogues(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    service: TravelogueService = Depends(get_travelogue_service),
):
    """当前用户的游记列表"""
    return BaseResponse(data=await service.list_by_user(
        user_id=current_user["user_id"], status=status, page=page, page_size=page_size))


@router.get("/by-trip/{trip_id}", response_model=BaseResponse[TravelogueResponse | None])
async def get_travelogue_by_trip(
    trip_id: str,
    current_user: dict = Depends(get_current_user),
    service: TravelogueService = Depends(get_travelogue_service),
    trip_service: TripService = Depends(get_trip_service),
):
    """查询当前用户一趟旅行的主游记。"""
    trip = await trip_service.get_trip(trip_id, current_user["user_id"])
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    result = await service.get_by_trip(trip_id)
    if result and result["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="无权操作")
    return BaseResponse(data=result)


# ==================== Social Materials ====================

@router.post("/materials/generate", response_model=BaseResponse[dict])
async def generate_materials(
    request: MaterialGenerateRequest,
    current_user: dict = Depends(get_current_user),
    trip_service: TripService = Depends(get_trip_service),
    travelogue_service: TravelogueService = Depends(get_travelogue_service),
):
    """一键生成社交素材（9宫格+卡片+合集）"""
    from app.agents.travelogue_agent import TravelogueAgent
    from app.services.llm.deepseek import DeepSeekLLM

    try:
        trip_context = await trip_service.get_travelogue_context(
            request.trip_id, current_user["user_id"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    agent = TravelogueAgent(DeepSeekLLM())
    result = await agent.generate_social_materials({
        "trip_id": request.trip_id,
        "checkins": trip_context["checkins"],
        "trip_info": trip_context,
    })

    # 持久化素材
    saved = []
    for m in result.get("materials", []):
        if m:
            saved_m = await travelogue_service.create_material(
                trip_id=request.trip_id, user_id=current_user["user_id"],
                type=m.get("type", ""), title=m.get("title"), content=m.get("content"),
                hashtags=m.get("hashtags", []), location_tag=m.get("location_tag"),
                images=m.get("images", []), layout=m.get("layout"),
                overlay_data=m.get("overlay_data"),
                source_day=m.get("source_day"), source_poi=m.get("source_poi"),
            )
            saved.append(saved_m)

    return BaseResponse(data={"materials": saved})


@router.get("/materials", response_model=BaseResponse[list[MaterialResponse]])
async def list_materials(
    trip_id: str = Query(...),
    type: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
    service: TravelogueService = Depends(get_travelogue_service),
):
    """社交素材列表"""
    _ = current_user
    return BaseResponse(data=await service.list_materials(trip_id, type))


@router.post("/materials/{material_id}/favorite",
             response_model=BaseResponse[MaterialResponse])
async def favorite_material(
    material_id: str,
    request: MaterialFavoriteRequest,
    current_user: dict = Depends(get_current_user),
    service: TravelogueService = Depends(get_travelogue_service),
):
    """收藏/取消收藏素材"""
    _ = current_user
    try:
        result = await service.favorite_material(material_id, request.is_favorite)
        return BaseResponse(data=result)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ==================== Shares ====================

@router.post("/shares", response_model=BaseResponse[ShareResponse])
async def create_share(
    request: ShareCreateRequest,
    current_user: dict = Depends(get_current_user),
    service: TravelogueService = Depends(get_travelogue_service),
):
    """生成分享链接"""
    import secrets
    import string as _string

    from sqlalchemy.exc import IntegrityError

    expire_at = None
    if request.expire_hours:
        expire_at = datetime.utcnow() + timedelta(hours=request.expire_hours)

    for attempt in range(3):
        share_code = ''.join(
            secrets.choice(_string.ascii_lowercase + _string.digits)
            for _ in range(8)
        )
        try:
            result = await service.create_share(
                user_id=current_user["user_id"],
                target_type=request.target_type, target_id=request.target_id,
                share_code=share_code, password=request.password, expire_at=expire_at,
            )
            return BaseResponse(data=result)
        except IntegrityError as exc:
            if attempt == 2:
                raise HTTPException(
                    status_code=500,
                    detail="生成分享链接失败，请重试",
                ) from exc


@router.get("/shares/{share_code}", response_model=BaseResponse[ShareResponse])
async def get_share(
    share_code: str,
    password: str | None = Query(default=None, description="访问密码"),
    service: TravelogueService = Depends(get_travelogue_service),
):
    """通过短码获取分享内容"""
    result = await service.get_share_by_code(share_code)
    if not result:
        raise HTTPException(status_code=404, detail="分享链接不存在")
    if result.get("has_password"):
        stored_password = await service.get_share_password(share_code)
        if not password or password != stored_password:
            raise HTTPException(status_code=403, detail="密码错误")
    await service.increment_view(share_code)
    return BaseResponse(data=result)


# 参数化路径必须放在 /materials 与 /shares 之后，避免吞掉静态路由。

@router.get("/{travelogue_id}", response_model=BaseResponse[TravelogueResponse])
async def get_travelogue(
    travelogue_id: str,
    current_user: dict = Depends(get_current_user),
    service: TravelogueService = Depends(get_travelogue_service),
):
    """游记详情"""
    _ = current_user
    result = await service.get(travelogue_id)
    if not result:
        raise HTTPException(status_code=404, detail="游记不存在")
    return BaseResponse(data=result)


@router.patch("/{travelogue_id}", response_model=BaseResponse[TravelogueResponse])
async def update_travelogue(
    travelogue_id: str,
    request: TravelogueUpdateRequest,
    current_user: dict = Depends(get_current_user),
    service: TravelogueService = Depends(get_travelogue_service),
):
    """编辑游记"""
    try:
        result = await service.update(
            travelogue_id,
            user_id=current_user["user_id"],
            title=request.title,
            content=request.content,
            cover_url=request.cover_url,
            status=request.status,
        )
        return BaseResponse(data=result)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.delete("/{travelogue_id}", response_model=BaseResponse[EmptyData])
async def delete_travelogue(
    travelogue_id: str,
    current_user: dict = Depends(get_current_user),
    service: TravelogueService = Depends(get_travelogue_service),
):
    """删除游记"""
    try:
        await service.delete_by_user(travelogue_id, current_user["user_id"])
        return BaseResponse(data=EmptyData())
    except ValueError as exc:
        return BaseResponse(code=404, message=str(exc), data=EmptyData())
    except PermissionError as exc:
        return BaseResponse(code=403, message=str(exc), data=EmptyData())


@router.post("/{travelogue_id}/publish", response_model=BaseResponse[TravelogueResponse])
async def publish_travelogue(
    travelogue_id: str,
    current_user: dict = Depends(get_current_user),
    service: TravelogueService = Depends(get_travelogue_service),
):
    """发布游记"""
    try:
        result = await service.publish(
            travelogue_id,
            user_id=current_user["user_id"],
        )
        return BaseResponse(data=result)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/{travelogue_id}/regenerate", response_model=BaseResponse[TravelogueResponse])
async def regenerate_section(
    travelogue_id: str,
    request: RegenerateSectionRequest,
    current_user: dict = Depends(get_current_user),
    travelogue_service: TravelogueService = Depends(get_travelogue_service),
    trip_service: TripService = Depends(get_trip_service),
):
    """局部重写某天内容"""
    import re

    from app.agents.travelogue_agent import TravelogueAgent
    from app.services.llm.deepseek import DeepSeekLLM

    travelogue = await travelogue_service.get(travelogue_id)
    if not travelogue:
        raise HTTPException(status_code=404, detail="游记不存在")
    if travelogue["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="无权操作")

    try:
        trip_context = await trip_service.get_travelogue_context(
            travelogue["trip_id"], current_user["user_id"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    day_checkins = [
        checkin for checkin in trip_context["checkins"]
        if int(checkin.get("source_day") or 1) == request.day
    ]
    planned_day = next((
        day for index, day in enumerate(trip_context["daily_itinerary"], start=1)
        if int(day.get("day") or index) == request.day
    ), {})
    result = await TravelogueAgent(DeepSeekLLM()).regenerate_section({
        "day": request.day,
        "checkins": day_checkins,
        "planned_day": planned_day,
        "style": request.style,
        "feedback": request.feedback or "",
        "destination": trip_context["destination"],
    })

    pattern = rf"(## Day {request.day}\n\n).*?(?=\n\n## Day |\n\n---|\Z)"
    content = travelogue.get("content") or ""
    new_content = re.sub(
        pattern,
        rf"\1{result['content']}",
        content,
        flags=re.DOTALL,
    )
    updated = await travelogue_service.update(
        travelogue_id,
        user_id=current_user["user_id"],
        content=new_content,
    )
    return BaseResponse(data=updated)
