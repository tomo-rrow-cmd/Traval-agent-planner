"""
Chat API — 文档 §4 五阶段流水线

POST /chat/sessions/{id}/messages  → 保存消息并返回 SSE
GET  /chat/sessions/{id}/stream   → SSE 流式跑 pipeline
"""

import asyncio
import contextlib
import json
import logging
import os
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse

from app.config import settings
from app.dependencies import get_conversation_service, get_current_user
from app.schemas.chat import (
    ChatMessageCreateRequest,
    ChatSession,
    ChatSessionCreateRequest,
    ChatSessionUpdateRequest,
    ConversationPlanRunRecord,
    MessageRecord,
)
from app.schemas.common import (
    BaseResponse, CursorPaginatedData, EmptyData, PaginatedData,
)
from app.services.application import ConversationService
from app.services.application.plan_result_message import (
    PLAN_RESULT_FORMAT,
    build_plan_result_message,
)

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = logging.getLogger(__name__)

_SSE_DONE = object()
_SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def _format_sse_frame(event_id: int, event: str, data: dict) -> str:
    return (
        f"id: evt_{event_id}\n"
        f"event: {event}\n"
        f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
    )


async def _enqueue_sse_events(events, queue: asyncio.Queue) -> None:
    try:
        if hasattr(events, "__aiter__"):
            async for item in events:
                await queue.put(item)
        else:
            for item in events:
                await queue.put(item)
    except Exception as exc:
        await queue.put(("error", {"message": str(exc)}))
    finally:
        await queue.put(_SSE_DONE)


def sse_response(
    events,
    keepalive: bool = True,
    keepalive_interval: float = 15.0,
) -> StreamingResponse:
    """SSE 流"""
    async def stream():
        queue: asyncio.Queue = asyncio.Queue(maxsize=1)
        producer = asyncio.create_task(_enqueue_sse_events(events, queue))
        idx = 0
        try:
            while True:
                if keepalive:
                    try:
                        item = await asyncio.wait_for(queue.get(), timeout=keepalive_interval)
                    except asyncio.TimeoutError:
                        yield ": keepalive\n\n"
                        continue
                else:
                    item = await queue.get()

                if item is _SSE_DONE:
                    break

                evt, data = item
                idx += 1
                yield _format_sse_frame(idx, evt, data)
        finally:
            if not producer.done():
                producer.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await producer
            else:
                with contextlib.suppress(Exception):
                    producer.result()

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


async def _run_pipeline_events(session_id: str, message: str,
                               user_id: str, history: list[dict],
                               service=None,
                               images: list[str] | None = None):
    """文档 §4：对话提取 → 5 阶段 pipeline → SSE"""

    from app.services.llm.deepseek import DeepSeekLLM
    from app.agents.user_interaction_agent import UserInteractionAgent

    llm = DeepSeekLLM()
    ui = UserInteractionAgent(llm)
    context = {}
    if service and hasattr(service, "get_session_context"):
        try:
            context = await service.get_session_context(user_id, session_id)
        except Exception:
            context = {}

    if images:
        context["uploaded_images"] = images

    # 阶段1: 对话提取
    yield ("step_start", {"step": "chat", "label": "分析对话中..."})

    res = None
    async for item in ui.stream_response({"message": message, "history": history, "context": context}):
        if item["type"] == "delta":
            yield ("message_delta", {
                "role": "assistant",
                "content_delta": item["content_delta"],
                "message_type": "text",
                "sequence": item["sequence"],
            })
        elif item["type"] == "result":
            res = item

    if res is None:
        yield ("error", {"message": "No assistant response generated"})
        return

    reply = res["reply"]
    ready = res.get("ready", False)
    mode = res.get("mode")
    confirmed = res.get("confirmed", False)
    extracted = res.get("extracted", {})

    yield ("message", {"role": "assistant", "content": reply, "message_type": "text"})

    if service:
        try:
            await service.record_ai_reply(
                session_id,
                reply,
                user_id=user_id,
                metadata={
                    "agent_status": res.get("status"),
                    "requested_fields": res.get("requested_fields", []),
                },
            )
        except Exception as e:
            logger.warning("record_ai_reply failed for session %s: %s", session_id, e)

    yield ("step_end", {"step": "chat"})

    if not (mode == "travel_planning" and ready and confirmed):
        logger.info("[N3.decision] NOT confirmed: mode=%s ready=%s confirmed=%s → waiting_input",
            mode, ready, confirmed)
        yield ("done", {"status": "waiting_input", "session_id": session_id})
        return

    logger.info("[N3.decision] CONFIRMED! mode=%s ready=%s confirmed=%s → starting pipeline",
        mode, ready, confirmed)

    # 阶段2-5: pipeline
    from app.orchestrator.pipeline import run_pipeline

    pipeline_params = {**extracted, "confirmed": confirmed}
    async for evt, data in run_pipeline(pipeline_params):
        if evt == "done":
            summary = data.get("summary") or {}
            logger.info("[N5.done] summary keys=%s", list(summary.keys()))
            summary = await _ensure_summary_data(summary)
            data["summary"] = summary
            data["result_message"] = build_plan_result_message(summary)
            data["result_format"] = PLAN_RESULT_FORMAT
            logger.info("[N5.llmfb] weather=%s meal=%s",
                len(summary.get("weather_forecast", []) or []),
                len(summary.get("meal_plan", []) or []))
            if service and hasattr(service, "persist_plan_result"):
                try:
                    logger.info("[N5] calling persist_plan_result...")
                    plan_run = await service.persist_plan_result(
                        user_id, session_id, summary,
                    )
                    data["plan_id"] = plan_run.id
                    logger.info("[N5] persist_plan_result OK plan_id=%s", plan_run.id)
                except Exception:
                    logger.exception(
                        "[N5] persist_plan_result FAILED for session %s",
                        session_id,
                    )
                    data["plan_id"] = f"plan_{session_id[:8]}"
            elif service and hasattr(service, "create_plan_run"):
                try:
                    plan_run = await service.create_plan_run(session_id, summary)
                    data["plan_id"] = plan_run.id
                except Exception:
                    logger.exception(
                        "[N5] create_plan_run FAILED for session %s",
                        session_id,
                    )
                    data["plan_id"] = f"plan_{session_id[:8]}"
            else:
                data["plan_id"] = f"plan_{session_id[:8]}"
            data["session_id"] = session_id
            logger.info("[N7] yielding done event plan_id=%s", data.get("plan_id"))
        else:
            logger.info("[N7] yielding %s event", evt)
        yield (evt, data)


async def _agent_sse_events(
    session_id: str,
    message: str,
    user_id: str,
    history: list[dict],
    service: ConversationService | None = None,
    images: list[str] | None = None,
):
    """对话 Agent SSE 事件源；API 契约测试可 monkeypatch 此函数。"""
    async for event in _run_pipeline_events(
        session_id,
        message,
        user_id,
        history,
        service=service,
        images=images,
    ):
        yield event


async def _load_history(service: ConversationService, user_id: str, session_id: str) -> list[dict]:
    history_data = await service.get_messages(user_id=user_id, session_id=session_id, limit=50)
    history_list = getattr(history_data, "list", getattr(history_data, "items", []))
    return [
        {
            "role": message.role,
            "content": message.content,
            "metadata": message.metadata,
        }
        for message in history_list
    ]


# ---- Routes ----

@router.post("/sessions", response_model=BaseResponse[ChatSession])
async def create_session(
    request: ChatSessionCreateRequest,
    current_user: dict = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    return BaseResponse(data=await service.create_session(current_user["user_id"], request))


@router.get("/sessions", response_model=BaseResponse[PaginatedData[ChatSession]])
async def list_sessions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    return BaseResponse(data=await service.list_sessions(current_user["user_id"], page=page, page_size=page_size))


@router.delete("/sessions/{session_id}", response_model=BaseResponse[EmptyData])
async def delete_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    await service.delete_session(current_user["user_id"], session_id)
    return BaseResponse(data=EmptyData())


@router.patch("/sessions/{session_id}", response_model=BaseResponse[ChatSession])
async def update_session(
    session_id: str,
    request: ChatSessionUpdateRequest,
    current_user: dict = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    return BaseResponse(data=await service.update_session(
        current_user["user_id"], session_id, request,
    ))


@router.post("/upload/image")
async def upload_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """上传图片 → 返回可访问的 URL"""
    _ = current_user  # 预留：后续可关联用户

    # 校验文件类型
    ALLOWED = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in ALLOWED:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file.content_type}，仅支持 jpg/png/webp")

    # 校验文件大小
    max_size = settings.UPLOAD_MAX_SIZE_MB * 1024 * 1024
    contents = await file.read()
    if len(contents) > max_size:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"文件过大，最大 {settings.UPLOAD_MAX_SIZE_MB}MB")

    # 保存文件
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    ext = file.filename.rsplit(".", 1)[-1] if "." in (file.filename or "") else "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = upload_dir / filename

    with open(filepath, "wb") as f:
        f.write(contents)

    url = f"/uploads/{filename}"
    logger.info(f"  [Upload] {file.filename} → {url} ({len(contents)} bytes)")
    return BaseResponse(data={"url": url, "filename": filename})


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    request: ChatMessageCreateRequest,
    current_user: dict = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    """保存用户消息并返回 Agent SSE 流"""
    _, created = await service.record_message(
        user_id=current_user["user_id"], session_id=session_id, request=request,
    )
    if not created:
        return sse_response([("done", {
            "status": "idempotent_replay",
            "client_message_id": request.client_message_id,
            "session_id": session_id,
        })])
    history = await _load_history(service, current_user["user_id"], session_id)
    return sse_response(_agent_sse_events(
        session_id,
        request.content,
        current_user["user_id"],
        history,
        service=service,
        images=request.images,
    ))


@router.get("/sessions/{session_id}/stream")
async def stream_session(
    session_id: str,
    last_event_id: str | None = Query(default=None, alias="lastEventId"),
    token: str | None = Query(default=None),
    service: ConversationService = Depends(get_conversation_service),
):
    """
    SSE 流式返回 Agent 规划结果（文档 §4 五阶段）。

    EventSource 不支持 Header，Token 通过 URL 参数传递。
    """
    _ = last_event_id

    user_id = "anonymous"
    if token:
        try:
            from app.core.security import decode_access_token
            user_id = decode_access_token(token)["sub"]
        except Exception:
            pass

    history = await _load_history(service, user_id, session_id)

    last_msg = ""
    for m in reversed(history):
        if m["role"] == "user":
            last_msg = m["content"]
            break

    return sse_response(_agent_sse_events(session_id, last_msg, user_id, history, service=service))


@router.get("/sessions/{session_id}/messages",
    response_model=BaseResponse[PaginatedData[MessageRecord] | CursorPaginatedData[MessageRecord]])
async def get_messages(
    session_id: str,
    page: int | None = Query(default=None, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    before_id: str | None = Query(default=None),
    after_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    return BaseResponse(data=await service.get_messages(
        user_id=current_user["user_id"], session_id=session_id,
        page=page, page_size=page_size, before_id=before_id, after_id=after_id, limit=limit,
    ))


@router.get("/sessions/{session_id}/plans",
    response_model=BaseResponse[list[ConversationPlanRunRecord]])
async def list_session_plans(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
):
    return BaseResponse(data=await service.list_plan_runs(current_user["user_id"], session_id))


async def _ensure_summary_data(summary: dict) -> dict:
    """当 summary 中天气/餐饮数据为空时，用 DeepSeek 生成回退数据"""
    dest = summary.get("destination", "")
    days = int(summary.get("days", 0) or 0)
    if not dest or not days:
        return summary

    need_weather = not summary.get("weather_forecast")
    need_meals = not summary.get("meal_plan") and not summary.get("food_details")
    need_trains = not summary.get("big_traffic") or (
        isinstance(summary.get("big_traffic"), list) and all(
            not item.get("trains") and not item.get("return_trains")
            for item in summary["big_traffic"]
        )
    )
    if not need_weather and not need_meals and not need_trains:
        return summary

    from app.services.llm.deepseek import DeepSeekLLM

    today = __import__('datetime').date.today().isoformat()
    prompt = f"目的地：{dest}，天数：{days}。\n"
    if need_weather:
        prompt += (
            f"生成{dest}从{today}开始的{days}天天气预报。"
            f"注意：今天的日期是{today}，返回的日期必须从{today}开始且年份是2026年。"
            f"JSON格式：{{'forecasts':[{{'date':'{today}','weather':'晴','temp_high':30,'temp_low':22,'wind':'南风3级','advice':'建议'}}]}}\n"
        )
    if need_meals:
        prompt += f"生成{dest}{days}天旅行三餐，JSON：{{'meal_plan':[{{'day':1,'meals':[{{'meal':'午餐','restaurant':'店名','avg_price':50,'reason':'理由'}},{{'meal':'晚餐','restaurant':'店名','avg_price':60,'reason':'理由'}}]}}]}}\n"
    if need_trains:
        origin = summary.get("origin", "")
        prompt += (
            f"生成从{origin}到{dest}的火车班次（去程和{days}天后返程），"
            f"JSON格式：{{\"big_traffic\":[{{\"trains\":[{{\"trainCode\":\"Gxxx\","
            f"\"fromStationName\":\"{origin}\",\"toStationName\":\"{dest}\","
            f"\"departureTime\":\"08:00\",\"arrivalTime\":\"12:00\",\"duration\":\"4h\","
            f"\"prices\":{{\"二等座\":500,\"一等座\":800}}}}],"
            f"\"return_trains\":[{{\"trainCode\":\"Gxxx\","
            f"\"fromStationName\":\"{dest}\",\"toStationName\":\"{origin}\","
            f"\"departureTime\":\"14:00\",\"arrivalTime\":\"18:00\",\"duration\":\"4h\","
            f"\"prices\":{{\"二等座\":500,\"一等座\":800}}}}]}}]}}\n"
        )
    prompt += "只返回JSON。"

    try:
        llm = DeepSeekLLM()
        resp = await asyncio.wait_for(llm.chat([{"role": "user", "content": prompt}]), timeout=30.0)
        data = _extract_json(resp)
        if need_weather and "forecasts" in data:
            summary["weather_forecast"] = data["forecasts"]
            logger.info("[llm_fallback] generated %d weather", len(data["forecasts"]))
            # 修正 LLM 生成的 2025 年日期
            this_year = __import__('datetime').date.today().year
            if this_year != 2025:
                for f in summary["weather_forecast"]:
                    fd = f.get("date", "")
                    if fd.startswith("2025-"):
                        f["date"] = str(this_year) + fd[4:]
        if need_meals and "meal_plan" in data:
            summary["meal_plan"] = data["meal_plan"]
            logger.info("[llm_fallback] generated %d meals", len(data["meal_plan"]))
        if need_trains and "big_traffic" in data:
            summary["big_traffic"] = data["big_traffic"]
            logger.info("[llm_fallback] generated %d traffic entries", len(data["big_traffic"]))
    except Exception as e:
        logger.warning("[llm_fallback] failed: %s", str(e)[:100])

    # === 预算更新：无论 meals 来自管道还是 LLM，只要存在就更新 ===
    meal_plan = summary.get("meal_plan") or []
    if isinstance(meal_plan, list) and meal_plan:
        total_meal_cost = sum(
            m.get("avg_price", 0) or 0
            for day in meal_plan
            for m in day.get("meals", [])
        )
        if total_meal_cost > 0:
            budget = summary.get("budget") or {}
            for d in budget.get("details") or []:
                if d.get("category") in ("餐饮", "food", "meal"):
                    d["spent"] = total_meal_cost
                    d["remaining"] = max(d.get("budget", 0) - total_meal_cost, 0)
                    d["status"] = "over" if total_meal_cost > d.get("budget", 0) else "ok"
                    break
            if budget.get("details"):
                new_actual = sum(d.get("spent", 0) for d in budget["details"])
                budget["actual_total"] = new_actual
                budget["remaining"] = max(budget.get("total_budget", 0) - new_actual, 0)
                logger.info("[llm_fallback] budget updated: meal_cost=%s total=%s",
                    total_meal_cost, new_actual)

    return summary


def _extract_json(text: str) -> dict:
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        text = m.group(1).strip()
    m = re.search(r"\{[\s\S]*\}", text)
    return json.loads(m.group(0)) if m else {}
