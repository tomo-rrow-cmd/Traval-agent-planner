"""
User Interaction Agent — 文档 §3.1

负责用户意图识别、旅行规划信息收集和规划前确认。
"""

import asyncio
import json
import re
from datetime import date, datetime
from typing import Any, AsyncIterator
from zoneinfo import ZoneInfo

from app.agents.base import BaseAgent
from app.utils.validator import resolve_trip_dates


def _clean(text: str) -> str:
    """Remove surrogate characters that break JSON encoding."""
    return text.encode("utf-8", errors="replace").decode("utf-8")


REQUIRED_FIELDS = ("origin", "destination", "start_date", "days", "total_budget", "preferences")
FIELD_LABELS = {
    "origin": "出发地",
    "destination": "目的地",
    "start_date": "出发日期",
    "days": "时长",
    "total_budget": "预算",
    "preferences": "偏好",
}
CONFIRMATION_MARKER = "确认后我再开始生成完整方案，可以吗？"
STREAM_CHUNK_SIZE = 8
STREAM_CHUNK_INTERVAL_SECONDS = 0.035

COLLECTION_PROMPT = """你是旅行规划助手，正在通过自然对话补齐核心参数。

当前已知参数和缺失参数：
{state}

最近对话：
{history}

只返回 JSON：
{{
  "reply": "自然、简洁的中文追问",
  "requested_fields": ["本轮询问的字段名"]
}}

要求：
- 只能询问 missing_fields 中的字段，每轮选择 1 至 2 个。
- 优先把 start_date 和 days、total_budget 和 preferences 组合询问。
- 先自然承接用户刚说的内容，再提出问题；不要像表单，不要复述字段名。
- 不要重复询问 known_fields 中已有的信息，不要虚构答案。
- 不要声称已经开始生成方案，也不要一次罗列所有问题。
- origin 是出发城市，destination 是目的地，preferences 是旅行偏好。
"""

ANALYZE_PROMPT = """你是旅行规划产品的用户交互理解器。请基于完整对话判断用户当前意图，并抽取旅行规划参数。

当前日期（Asia/Shanghai）: {today}

完整对话:
{history}

只返回 JSON，不要解释：
{{
  "mode": "travel_planning 或 daily_chat",
  "extracted": {{
    "destination": "",
    "origin": "",
    "start_date": "",
    "end_date": "",
    "days": 0,
    "total_budget": 0,
    "reserve_budget": 0,
    "planning_budget": 0,
    "budget_no_limit": false,
    "preferences": [],
    "cuisine_preferences": [],
    "preferred_transport": "地铁",
    "preferred_transport_provided": false,
    "preferences_provided": false,
    "pace": "适中",
    "hotel_star": 3,
    "hotel_budget": 500,
    "meal_budget": 100,
    "travelers": 1
  }},
  "ambiguous_fields": []
}}

规则：
- 只有用户明确要求规划旅行、排行程、做路线/旅行方案，或正在延续前文的信息收集/确认流程时，mode 才是 travel_planning。
- 普通闲聊、知识问答、单纯询问某地怎么玩/天气/景点介绍，mode 是 daily_chat。
- 从完整历史中抽取参数；较新的用户修正覆盖较早信息。
- 如果用户在完成一次规划后明确说“再规划一个/重新规划/另外我想从A到B玩N天”，把它视为新的旅行规划；不要沿用上一份方案字段，除非用户明确说“沿用上次预算/偏好”。
- 如果同一字段冲突且无法判断最新有效值，把该字段留空或置 0，并写入 ambiguous_fields。
- 必填规划参数是 origin 出发地、destination 目的地、start_date 出发日期、days/end_date 行程时长、total_budget 总预算、preferences 偏好。
- 日期输出必须是 YYYY-MM-DD。相对日期必须基于上面的 Asia/Shanghai 当前日期转换成明确日期，例如“下周五”输出具体 ISO 日期。
- 支持 start_date+days 或 start_date+end_date；如果用户同时提供 end_date 和 days，请原样输出，不要自行覆盖冲突。
- 旅行偏好和菜系偏好必须分离：历史、人文、亲子、自然风光进入 preferences；川菜、粤菜、素食、清真、不吃辣进入 cuisine_preferences。
- 只有菜系/饮食偏好时，preferences 可以为空，但 preferences_provided 必须为 true。
- preferred_transport 只输出 地铁、步行、自驾、打车；未明确交通方式时输出 地铁。
- 只有用户明确提到交通或出行方式时 preferred_transport_provided 才输出 true。
- 用户说“留/预留 N 元应急/备用/机动”时，reserve_budget 为 N，planning_budget 为 total_budget - reserve_budget。
- 用户说“无偏好/随便/都可以/不限偏好”时，preferences 为空数组，但 preferences_provided 必须为 true。
- 用户说预算不限时，budget_no_limit 为 true，total_budget 可为 0。
- 数字请转成阿拉伯数字，例如“三天”=>3，“五千”=>5000，“一个周末”=>2。
- origin 是从哪里出发，destination 是去哪里。"""

DAILY_CHAT_PROMPT = """你是一个自然、友好的中文助手。请直接回答用户当前问题，不要自称具体公司或模型。

规则：
- 优先响应用户最新一条消息，旧对话只作为背景，不要把旧目的地、旧预算和新话题混成正在执行的方案。
- 用户只是说想去、放弃、换一个目的地时，只围绕这个最新目的地或取舍聊天；不要主动确认旅行规划，不要说正在生成方案。
- 除非用户明确询问“还有哪些选择/推荐几个地方”，不要主动展开无关备选城市清单。
- 不要在闲聊模式输出完整旅行方案、Day-by-Day 行程、预算表或交通住宿明细；正式方案只能由结构化规划流程生成。
- 如果语境自然，可以在最后轻轻带一句：需要正式规划时，可以直接说“重新规划/生成方案”。不要生硬推销，不要说自己正在切换模式。"""


class UserInteractionAgent(BaseAgent):
    name = "user_interaction"
    description = "Detect intent, collect travel inputs, and require confirmation"

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        turns, history_text = self._prepare_history(input_data)
        context = input_data.get("context", {}) if isinstance(input_data.get("context"), dict) else {}
        current_user = self._last_user_text(turns)
        has_completed_plan = self._has_completed_plan(context)
        turn_intent = self._current_turn_intent(current_user)
        new_plan_now = turn_intent["requests_planning"]
        continuing_new_plan = has_completed_plan and self._has_active_planning_prompt(turns)

        if has_completed_plan and not new_plan_now and not continuing_new_plan:
            reply = await self._daily_chat_reply(turns, context)
            return self._result(
                reply=reply,
                mode="daily_chat",
                status="chat",
                extracted=self._normalize_extracted({}, self._user_history_text(turns)),
                missing_fields=[],
                confirmed=False,
                ready=False,
            )

        scoped_turns = turns
        is_new_plan = False
        if has_completed_plan and (new_plan_now or continuing_new_plan):
            scoped_turns = self._scope_to_current_planning_run(turns)
            history_text = self._history_text(scoped_turns)
            is_new_plan = True

        analysis = await self._analyze(history_text, self._user_history_text(scoped_turns))
        result = await self._build_result(
            analysis=analysis,
            turns=scoped_turns,
            context=context,
            full_turns=turns,
            is_new_plan=is_new_plan,
            turn_intent=turn_intent,
        )
        return result

    async def stream_response(self, input_data: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        """流式回复：普通聊天使用模型原生流，结构化回复使用可见的分片流。"""
        turns, history_text = self._prepare_history(input_data)
        context = input_data.get("context", {}) if isinstance(input_data.get("context"), dict) else {}
        current_user = self._last_user_text(turns)
        has_completed_plan = self._has_completed_plan(context)
        turn_intent = self._current_turn_intent(current_user)
        new_plan_now = turn_intent["requests_planning"]
        continuing_new_plan = has_completed_plan and self._has_active_planning_prompt(turns)

        daily_chat_turns: list[dict] | None = None
        daily_chat_extracted: dict[str, Any] | None = None
        result: dict[str, Any] | None = None

        # 已完成方案后的日常对话不再重复做意图分析。
        if has_completed_plan and not new_plan_now and not continuing_new_plan:
            daily_chat_turns = turns
            daily_chat_extracted = self._normalize_extracted(
                {}, self._user_history_text(turns),
            )
        else:
            scoped_turns = turns
            is_new_plan = False
            if has_completed_plan and (new_plan_now or continuing_new_plan):
                scoped_turns = self._scope_to_current_planning_run(turns)
                history_text = self._history_text(scoped_turns)
                is_new_plan = True

            analysis = await self._analyze(
                history_text,
                self._user_history_text(scoped_turns),
            )
            planning_authorized = (
                is_new_plan
                or turn_intent["requests_planning"]
                or self._has_active_planning_prompt(scoped_turns)
            )
            if not planning_authorized:
                daily_chat_turns = scoped_turns
                daily_chat_extracted = self._normalize_extracted(
                    analysis.get("extracted", {}),
                    self._user_history_text(scoped_turns),
                )
            else:
                result = await self._build_result(
                    analysis=analysis,
                    turns=scoped_turns,
                    context=context,
                    full_turns=turns,
                    is_new_plan=is_new_plan,
                    turn_intent=turn_intent,
                )

        if daily_chat_turns is not None and daily_chat_extracted is not None:
            sequence = 0
            full_reply = ""
            async for raw_chunk in self._daily_chat_reply_stream(daily_chat_turns, context):
                visible_chunks = self._visible_stream_chunks(raw_chunk)
                for index, chunk in enumerate(visible_chunks):
                    sequence += 1
                    full_reply += chunk
                    yield {"type": "delta", "content_delta": chunk, "sequence": sequence}
                    if index < len(visible_chunks) - 1:
                        await asyncio.sleep(STREAM_CHUNK_INTERVAL_SECONDS)
            yield {"type": "result", **self._result(
                reply=_clean(full_reply.strip()),
                mode="daily_chat",
                status="chat",
                extracted=daily_chat_extracted,
                missing_fields=[],
                confirmed=False,
                ready=False,
            )}
            return

        if result is None:
            return
        reply = result.get("reply", "")
        visible_chunks = self._visible_stream_chunks(reply)
        for sequence, chunk in enumerate(visible_chunks, start=1):
            yield {"type": "delta", "content_delta": chunk, "sequence": sequence}
            if sequence < len(visible_chunks):
                await asyncio.sleep(STREAM_CHUNK_INTERVAL_SECONDS)
        yield {"type": "result", **result}

    @staticmethod
    def _visible_stream_chunks(text: str) -> list[str]:
        """将非流式生成的短回复切成浏览器可逐帧呈现的片段。"""
        cleaned = _clean(text or "")
        return [
            cleaned[index:index + STREAM_CHUNK_SIZE]
            for index in range(0, len(cleaned), STREAM_CHUNK_SIZE)
        ]

    def _prepare_history(self, input_data: dict[str, Any]) -> tuple[list[dict], str]:
        message = str(input_data.get("message", "") or "")
        history = list(input_data.get("history", []) or [])
        context = input_data.get("context", {}) if isinstance(input_data.get("context"), dict) else {}

        # 将上传的图片 URL 注入到最新一条用户消息的上下文中
        uploaded_images: list[str] = context.get("uploaded_images") or []
        if uploaded_images:
            image_note = f"\n[用户上传了 {len(uploaded_images)} 张图片，图片 URL 列表：{', '.join(uploaded_images)}]"
            if message:
                message = message + image_note

        last_is_current_user = (
            history
            and history[-1].get("role") == "user"
            and (not message or history[-1].get("content") == message)
        )
        if not last_is_current_user:
            history.append({"role": "user", "content": message})

        history_text = "\n".join(
            f"{m.get('role', '')}: {m.get('content', '')}" for m in history
        )
        return history, history_text

    async def _analyze(self, history_text: str, user_text: str = "") -> dict[str, Any]:
        try:
            today = self._today_shanghai()
            resp = await self.call_llm(
                [{
                    "role": "user",
                    "content": ANALYZE_PROMPT.format(
                        history=history_text,
                        today=today.isoformat(),
                    ),
                }],
                temperature=0.1,
            )
            parsed = self._parse_json_object(resp)
            if parsed:
                parsed["extracted"] = self._normalize_extracted(
                    parsed.get("extracted", {}),
                    user_text,
                )
                return parsed
        except Exception:
            pass

        return {
            "mode": "daily_chat",
            "extracted": self._normalize_extracted({}, user_text),
            "ambiguous_fields": [],
        }

    async def _build_result(
        self,
        analysis: dict[str, Any],
        turns: list[dict],
        context: dict[str, Any] | None = None,
        full_turns: list[dict] | None = None,
        is_new_plan: bool = False,
        turn_intent: dict[str, bool] | None = None,
    ) -> dict[str, Any]:
        context = context or {}
        turn_intent = turn_intent or self._current_turn_intent(self._last_user_text(turns))
        planning_authorized = (
            is_new_plan
            or turn_intent["requests_planning"]
            or self._has_active_planning_prompt(turns)
        )
        mode = "travel_planning" if planning_authorized else "daily_chat"

        extracted = self._normalize_extracted(
            analysis.get("extracted", {}),
            self._user_history_text(turns),
        )
        if self._is_confirmed(turns):
            extracted = self._merge_trip_data(
                extracted,
                self._latest_confirmed_trip(turns),
            )
        if is_new_plan and full_turns:
            extracted = self._apply_inherited_fields(
                extracted,
                full_turns,
                self._user_history_text(turns),
                context,
                turn_intent,
            )
        if self._has_completed_plan(context):
            extracted["planning_run_index"] = int(context.get("plan_run_count") or 0) + (1 if is_new_plan else 0)

        if mode == "travel_planning":
            date_result = resolve_trip_dates(
                extracted.get("start_date"),
                extracted.get("end_date"),
                extracted.get("days"),
                today=self._today_shanghai(),
            )
            if date_result.get("ok"):
                extracted["start_date"] = date_result["start_date"]
                extracted["end_date"] = date_result["end_date"]
                extracted["days"] = date_result["days"]
            elif date_result.get("error_code") not in {
                "missing_duration",
                "missing_start_date",
            }:
                missing = ["start_date"] if date_result.get("error_code") == "missing_start_date" else []
                return self._result(
                    reply=self._date_error_reply(date_result),
                    mode="travel_planning",
                    status="collecting",
                    extracted=extracted,
                    missing_fields=missing,
                    confirmed=False,
                    ready=False,
                )

        ambiguous = [
            field for field in analysis.get("ambiguous_fields", [])
            if field in REQUIRED_FIELDS
        ]

        if mode != "travel_planning":
            reply = await self._daily_chat_reply(turns, context)
            return self._result(
                reply=reply,
                mode="daily_chat",
                status="chat",
                extracted=extracted,
                missing_fields=[],
                confirmed=False,
                ready=False,
            )

        actual_missing = self._missing_fields(extracted)
        ambiguous_missing = [field for field in ambiguous if field in actual_missing]
        missing = list(dict.fromkeys([*ambiguous_missing, *actual_missing]))
        confirmed = self._is_confirmed(turns)

        if missing:
            reply, requested_fields = await self._collection_reply(
                extracted,
                missing,
                turns,
            )
            return self._result(
                reply=reply,
                mode="travel_planning",
                status="collecting",
                extracted=extracted,
                missing_fields=missing,
                confirmed=False,
                ready=False,
                requested_fields=requested_fields,
            )

        if not confirmed:
            return self._result(
                reply=self._confirmation_reply(extracted),
                mode="travel_planning",
                status="awaiting_confirmation",
                extracted=extracted,
                missing_fields=[],
                confirmed=False,
                ready=False,
            )

        return self._result(
            reply="好的，我现在开始生成完整旅行方案。",
            mode="travel_planning",
            status="confirmed",
            extracted=extracted,
            missing_fields=[],
            confirmed=True,
            ready=True,
        )

    async def _daily_chat_reply_stream(
        self,
        turns: list[dict],
        context: dict[str, Any] | None = None,
    ) -> AsyncIterator[str]:
        """Daily chat 回复的流式版本，逐 token 产出。"""
        context = context or {}
        current_user = self._last_user_text(turns)

        # 模板回复（非 LLM）→ 一次产出
        if self._looks_like_new_plan(current_user):
            yield "可以，我先帮你整理成新的旅行规划。请补充出发地、天数、预算和偏好；如果要沿用上次配置，也可以直接说。"
            return
        previous_assistant = self._last_assistant_before_current_user(turns)
        if self._looks_positive(current_user) and self._assistant_promised_unstructured_plan(previous_assistant):
            yield "可以。正式生成方案需要先进入规划流程；如果要沿用之前条件重新生成，请直接说“按照之前配置重新规划”。"
            return
        if self._looks_like_travel_generation_request(current_user):
            yield "可以，我先帮你进入正式规划流程。请补充出发地、目的地、天数、预算和偏好；如果沿用之前条件，也可以直接说明。"
            return

        # LLM 回复 → 流式产出
        messages = [{"role": "system", "content": DAILY_CHAT_PROMPT}]
        if self._has_completed_plan(context):
            completed_context = (
                "当前会话已经完成过一份旅行方案。现在不要进入结构化规划，"
                "只围绕最新话题做普通讨论；除非用户明确说重新规划/生成方案/帮我做行程，"
                "否则不要确认规划参数，不要说正在生成方案。"
            )
            summary_text = self._latest_plan_summary_text(context)
            if summary_text:
                completed_context += (
                    f" 已完成方案背景：{summary_text}。"
                    "如果引用这些旧条件，必须显式说“如果仍按之前条件”。"
                )
            messages.append({"role": "system", "content": completed_context})
        messages.extend(turns[-4:])

        try:
            async for chunk in self.call_llm_stream(messages, temperature=0.7):
                if chunk:
                    yield _clean(chunk)
        except Exception:
            yield "可以的。等你想规划旅行时，我也可以帮你一起梳理出发地、目的地、天数、预算和偏好。"

    async def _daily_chat_reply(
        self,
        turns: list[dict],
        context: dict[str, Any] | None = None,
    ) -> str:
        """非流式包装：收集 _daily_chat_reply_stream 的完整结果。"""
        parts = []
        async for chunk in self._daily_chat_reply_stream(turns, context):
            parts.append(chunk)
        return "".join(parts)

    @staticmethod
    def _result(
        reply: str,
        mode: str,
        status: str,
        extracted: dict[str, Any],
        missing_fields: list[str],
        confirmed: bool,
        ready: bool,
        requested_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "reply": _clean(reply),
            "mode": mode,
            "status": status,
            "extracted": extracted,
            "missing_fields": missing_fields,
            "confirmed": confirmed,
            "ready": ready,
            "requested_fields": requested_fields or [],
        }

    @staticmethod
    def _parse_json_object(text: str) -> dict[str, Any]:
        match = re.search(r"\{[\s\S]*\}", text or "")
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @classmethod
    def _normalize_extracted(cls, raw: Any, history_text: str = "") -> dict[str, Any]:
        raw = raw if isinstance(raw, dict) else {}
        raw_preferences = cls._normalize_preferences(raw.get("preferences"))
        raw_cuisine = cls._normalize_preferences(raw.get("cuisine_preferences"))
        preferences, cuisine_preferences = cls._split_preferences(raw_preferences)
        cuisine_preferences = cls._dedupe_list([*cuisine_preferences, *raw_cuisine])
        budget_no_limit = cls._to_bool(raw.get("budget_no_limit"))
        total_budget = cls._to_float(raw.get("total_budget"))
        reserve_budget = cls._to_float(raw.get("reserve_budget"))
        if reserve_budget <= 0:
            reserve_budget = cls._extract_reserve_budget(history_text)
        if budget_no_limit and total_budget <= 0:
            total_budget = 100000.0
        planning_budget = cls._to_float(raw.get("planning_budget"))
        if planning_budget <= 0:
            planning_budget = max(total_budget - reserve_budget, 0.0) if total_budget > 0 else 0.0
        if budget_no_limit:
            reserve_budget = 0.0
            planning_budget = total_budget

        preferences_provided = (
            cls._to_bool(raw.get("preferences_provided"))
            or bool(preferences)
            or bool(cuisine_preferences)
            or cls._mentions_no_preference(history_text)
        )
        preferred_transport_provided = (
            cls._to_bool(raw.get("preferred_transport_provided"))
            or cls._mentions_field_override(history_text, "preferred_transport")
        )

        return {
            "destination": cls._to_str(raw.get("destination")),
            "origin": cls._to_str(raw.get("origin")),
            "start_date": cls._to_str(raw.get("start_date")),
            "end_date": cls._to_str(raw.get("end_date")),
            "days": cls._to_int(raw.get("days")),
            "total_budget": total_budget,
            "reserve_budget": reserve_budget,
            "planning_budget": planning_budget,
            "budget_no_limit": budget_no_limit,
            "preferences": preferences,
            "cuisine_preferences": cuisine_preferences,
            "preferred_transport": cls._normalize_transport(raw.get("preferred_transport")),
            "preferred_transport_provided": preferred_transport_provided,
            "preferences_provided": preferences_provided,
            "pace": cls._to_str(raw.get("pace")) or "适中",
            "hotel_star": cls._to_int(raw.get("hotel_star")) or 3,
            "hotel_budget": cls._to_float(raw.get("hotel_budget")) or 500.0,
            "meal_budget": cls._to_float(raw.get("meal_budget")) or 100.0,
            "travelers": cls._to_int(raw.get("travelers")) or 1,
            "planning_run_id": cls._to_str(raw.get("planning_run_id")),
            "planning_run_index": cls._to_int(raw.get("planning_run_index")),
        }

    @staticmethod
    def _normalize_preferences(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if not isinstance(value, str):
            return []
        text = value.strip()
        if not text or UserInteractionAgent._mentions_no_preference(text):
            return []
        return [
            item.strip()
            for item in re.split(r"[,，、/；;\s]+", text)
            if item.strip()
        ]

    @staticmethod
    def _split_preferences(preferences: list[str]) -> tuple[list[str], list[str]]:
        travel = []
        cuisine = []
        for item in preferences:
            if UserInteractionAgent._is_cuisine_preference(item):
                cuisine.append(item)
            else:
                travel.append(item)
        return UserInteractionAgent._dedupe_list(travel), UserInteractionAgent._dedupe_list(cuisine)

    @staticmethod
    def _is_cuisine_preference(value: str) -> bool:
        text = re.sub(r"\s+", "", value or "")
        if not text:
            return False
        cuisine_terms = (
            "菜", "火锅", "烤鸭", "小吃", "素食", "素菜", "清真", "不吃辣",
            "少辣", "微辣", "辣", "甜食", "海鲜", "烧烤", "烤肉", "面食",
            "粤式", "川味", "本帮", "湘味", "东北菜", "西餐", "日料", "韩餐",
        )
        return any(term in text for term in cuisine_terms)

    @staticmethod
    def _dedupe_list(values: list[str]) -> list[str]:
        result = []
        seen = set()
        for value in values:
            item = str(value).strip()
            if item and item not in seen:
                seen.add(item)
                result.append(item)
        return result

    @staticmethod
    def _normalize_transport(value: Any) -> str:
        text = re.sub(r"\s+", "", str(value or "")).lower()
        if not text:
            return "地铁"
        if any(term in text for term in ("步行", "走路", "徒步", "walking", "walk")):
            return "步行"
        if any(term in text for term in ("打车", "出租", "网约车", "taxi", "叫车")):
            return "打车"
        if any(term in text for term in ("自驾", "开车", "driving", "drive")):
            return "自驾"
        if any(term in text for term in ("公交", "巴士", "地铁", "公共交通", "transit", "subway", "metro", "bus")):
            return "地铁"
        return "地铁"

    @staticmethod
    def _missing_fields(extracted: dict[str, Any]) -> list[str]:
        missing = []
        if not extracted.get("start_date"):
            missing.append("start_date")
        if not extracted.get("origin"):
            missing.append("origin")
        if not extracted.get("destination"):
            missing.append("destination")
        if int(extracted.get("days") or 0) <= 0:
            missing.append("days")
        budget_value = extracted.get("planning_budget") if not extracted.get("budget_no_limit") else extracted.get("total_budget")
        if float(budget_value or 0) <= 0:
            missing.append("total_budget")
        if not extracted.get("preferences_provided"):
            missing.append("preferences")
        return missing

    @staticmethod
    def _question_for_missing_field(field: str) -> str:
        questions = {
            "start_date": "请告诉我具体出发日期，格式可以是 YYYY-MM-DD，也可以说“8月10日”这类明确日期。",
            "origin": "请告诉我你从哪个城市出发？",
            "destination": "想去哪个目的地呢？",
            "days": "这次计划玩几天？",
            "total_budget": "这次旅行总预算大概是多少？如果预算不限也可以直接说。",
            "preferences": (
                "你有什么旅行偏好吗？比如自然风光、历史人文、美食、亲子、轻松慢游；"
                "如果没有偏好也可以说“无偏好”。"
            ),
        }
        return questions.get(field, f"请补充{FIELD_LABELS.get(field, field)}。")

    async def _collection_reply(
        self,
        extracted: dict[str, Any],
        missing: list[str],
        turns: list[dict],
    ) -> tuple[str, list[str]]:
        known_fields = {
            field: extracted.get(field)
            for field in REQUIRED_FIELDS
            if field not in missing
        }
        state = json.dumps(
            {"known_fields": known_fields, "missing_fields": missing},
            ensure_ascii=False,
        )
        try:
            response = await self.call_llm(
                [{
                    "role": "user",
                    "content": COLLECTION_PROMPT.format(
                        state=state,
                        history=self._history_text(turns[-6:]),
                    ),
                }],
                temperature=0.7,
            )
            parsed = self._parse_json_object(response)
            reply = self._to_str(parsed.get("reply"))
            requested = parsed.get("requested_fields")
            if (
                reply
                and isinstance(requested, list)
                and 1 <= len(requested) <= 2
                and all(field in missing for field in requested)
                and len(set(requested)) == len(requested)
            ):
                return _clean(reply), requested
        except Exception:
            pass

        requested = self._fallback_collection_fields(missing)
        return self._fallback_collection_reply(requested), requested

    @staticmethod
    def _fallback_collection_fields(missing: list[str]) -> list[str]:
        pairs = (
            ("origin", "destination"),
            ("start_date", "days"),
            ("total_budget", "preferences"),
        )
        for first, second in pairs:
            if first in missing and second in missing:
                return [first, second]
        return missing[:1]

    @staticmethod
    def _fallback_collection_reply(fields: list[str]) -> str:
        pair_questions = {
            ("origin", "destination"): "这趟准备从哪里出发，目的地想定在哪座城市？",
            ("start_date", "days"): "你大概哪天出发，准备玩几天？",
            ("total_budget", "preferences"): (
                "这次总预算大概是多少，更偏爱自然风光、历史人文、美食，还是轻松慢游？"
            ),
        }
        pair = tuple(fields)
        if pair in pair_questions:
            return pair_questions[pair]
        return UserInteractionAgent._question_for_missing_field(fields[0])

    @staticmethod
    def _date_error_reply(result: dict[str, Any]) -> str:
        code = result.get("error_code")
        if code == "missing_start_date":
            return UserInteractionAgent._question_for_missing_field("start_date")
        if code == "date_days_conflict":
            return (
                "你提供的日期范围和行程天数不一致："
                f"日期范围代表 {result.get('derived_days')} 天，"
                f"但你填写的是 {result.get('provided_days')} 天。"
                "请确认按日期范围规划，还是按天数重新计算返程日期？"
            )
        return str(result.get("message") or "请补充有效的旅行日期。")

    @staticmethod
    def _confirmation_reply(extracted: dict[str, Any]) -> str:
        preferences = extracted.get("preferences") or []
        pref_text = "、".join(preferences) if preferences else "无偏好"
        cuisine = extracted.get("cuisine_preferences") or []
        cuisine_text = "、".join(cuisine) if cuisine else "无"
        date_text = f"{extracted.get('start_date')} 至 {extracted.get('end_date')}"
        budget_text = (
            "不限"
            if extracted.get("budget_no_limit")
            else f"¥{UserInteractionAgent._format_number(extracted.get('total_budget', 0))}"
        )
        reserve = float(extracted.get("reserve_budget") or 0)
        planning_budget = float(extracted.get("planning_budget") or 0)
        if reserve > 0:
            budget_text = (
                f"总预算 {budget_text}，其中 ¥{UserInteractionAgent._format_number(reserve)} 留作应急，"
                f"本次按 ¥{UserInteractionAgent._format_number(planning_budget)} 安排行程"
            )
        parts = (
            "我理解的信息是："
            f"从 {extracted.get('origin')} 出发，"
            f"去 {extracted.get('destination')}，"
            f"日期 {date_text}，"
            f"玩 {extracted.get('days')} 天，"
            f"预算 {budget_text}，"
            f"偏好 {pref_text}，"
            f"菜系 {cuisine_text}"
        )
        if extracted.get("preferred_transport_provided"):
            parts += f"，交通 {extracted.get('preferred_transport') or '地铁'}"
        return f"{parts}。{CONFIRMATION_MARKER}"

    @staticmethod
    def _is_confirmed(turns: list[dict]) -> bool:
        current_user = ""
        previous_assistant = ""

        for idx in range(len(turns) - 1, -1, -1):
            if turns[idx].get("role") == "user":
                current_user = str(turns[idx].get("content", ""))
                for prev in range(idx - 1, -1, -1):
                    if turns[prev].get("role") == "assistant":
                        previous_assistant = str(turns[prev].get("content", ""))
                        break
                break

        if CONFIRMATION_MARKER not in previous_assistant:
            return False
        if UserInteractionAgent._looks_negative(current_user):
            return False
        if UserInteractionAgent._looks_like_revision(current_user):
            return False
        return UserInteractionAgent._looks_positive(current_user)

    @staticmethod
    def _looks_positive(text: str) -> bool:
        lowered = text.strip().lower()
        if re.fullmatch(r"(?:嗯+|嗯哼|行|好呀|可以的|对的)", lowered):
            return True
        positive_terms = (
            "确认", "可以", "好的", "好", "没问题", "没错", "开始规划", "开始生成",
            "就这样", "对", "正确", "同意", "ok", "okay", "yes", "yep", "sure",
            "go ahead", "confirm", "按这个", "按照这个", "就按这个", "就按照这个",
        )
        return any(term in lowered for term in positive_terms)

    @staticmethod
    def _looks_negative(text: str) -> bool:
        lowered = text.strip().lower()
        negative_terms = (
            "不可以", "不确认", "不是", "不对", "先别", "不要", "取消", "等一下",
            "等等", "不行", "否", "no", "not yet", "hold on", "cancel",
        )
        return any(term in lowered for term in negative_terms)

    @staticmethod
    def _looks_like_revision(text: str) -> bool:
        lowered = text.strip().lower()
        if not UserInteractionAgent._looks_positive(lowered):
            return False
        revision_terms = (
            "不过", "但是", "改", "换", "调整", "预算", "出发", "目的地",
            "去", "玩", "天", "日期", "时间", "菜系", "口味", "交通",
            "步行", "地铁", "打车", "自驾", "偏好", "喜欢", "不喜欢",
        )
        return any(term in lowered for term in revision_terms)

    @staticmethod
    def _mentions_no_preference(text: str) -> bool:
        return bool(re.search(r"(无偏好|没有偏好|没偏好|随便|都可以|都行|不限偏好|不挑)", text or ""))

    @staticmethod
    def _history_text(turns: list[dict]) -> str:
        return "\n".join(f"{m.get('role', '')}: {m.get('content', '')}" for m in turns)

    @staticmethod
    def _user_history_text(turns: list[dict]) -> str:
        return "\n".join(str(m.get("content", "")) for m in turns if m.get("role") == "user")

    @staticmethod
    def _last_user_text(turns: list[dict]) -> str:
        for turn in reversed(turns):
            if turn.get("role") == "user":
                return str(turn.get("content", ""))
        return ""

    @staticmethod
    def _to_str(value: Any) -> str:
        return str(value).strip() if value is not None else ""

    @staticmethod
    def _today_shanghai() -> date:
        return datetime.now(ZoneInfo("Asia/Shanghai")).date()

    @staticmethod
    def _to_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes", "y", "是", "对"}
        return bool(value)

    @staticmethod
    def _to_int(value: Any) -> int:
        try:
            return int(float(str(value).strip()))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _to_float(value: Any) -> float:
        if value is None:
            return 0.0
        text = str(value).strip().replace(",", "").replace("，", "")
        text = re.sub(r"[¥￥元块\s]", "", text)
        match = re.search(r"\d+(?:\.\d+)?", text)
        if match:
            return float(match.group(0))
        try:
            return float(text)
        except ValueError:
            return 0.0

    @staticmethod
    def _format_number(value: Any) -> str:
        number = float(value or 0)
        if number.is_integer():
            return str(int(number))
        return f"{number:.2f}".rstrip("0").rstrip(".")

    @staticmethod
    def _has_completed_plan(context: dict[str, Any]) -> bool:
        return bool(
            context.get("has_completed_plan")
            or context.get("latest_plan_id")
            or context.get("session_status") == "completed"
        )

    @staticmethod
    def _current_turn_intent(text: str) -> dict[str, bool]:
        normalized = re.sub(r"\s+", "", text or "").lower()
        if not normalized:
            return {
                "requests_planning": False,
                "inherits_previous_config": False,
                "auto_confirm": False,
            }

        inherits_previous_config = UserInteractionAgent._looks_like_full_config_inheritance(normalized)
        auto_confirm = UserInteractionAgent._looks_like_auto_confirmed_replan(normalized)
        destination_change = bool(UserInteractionAgent._extract_destination_change(normalized))

        explicit_terms = (
            "再规划", "重新规划", "新规划", "另一个规划", "另外规划",
            "生成方案", "生成行程", "重新生成", "重新生成方案", "重新生成行程",
            "重做行程", "重新做行程", "重新排行程",
            "做方案", "旅行方案", "做行程", "排行程",
            "安排路线", "规划路线", "帮我规划", "帮我做行程", "帮我安排",
        )
        explicit_planning = any(term in normalized for term in explicit_terms)
        replan_cue = re.search(
            r"(?:重新|重做|生成|行程|方案|规划|沿用|照旧|不变|其他不变|相同配置|同样配置)",
            normalized,
        )
        has_route = re.search(
            r"(?:从|由).{1,20}(?:出发)?(?:去|到).{1,20}",
            normalized,
        )
        has_duration = re.search(
            r"(?:\d+|[一二两三四五六七八九十]+)天|周末|"
            r"(?:\d{4}-\d{1,2}-\d{1,2}|\d{1,2}月\d{1,2}日?)"
            r"(?:至|到|~|～|-)(?:\d{4}-\d{1,2}-\d{1,2}|\d{1,2}月\d{1,2}日?)",
            normalized,
        )
        has_budget = re.search(r"(?:预算|¥|￥|\d+(?:元|块)|预算不限|不限预算)", normalized)
        requests_planning = bool(
            explicit_planning
            or auto_confirm
            or (destination_change and (inherits_previous_config or replan_cue))
            or (has_route and has_duration and has_budget)
        )
        return {
            "requests_planning": requests_planning,
            "inherits_previous_config": inherits_previous_config,
            "auto_confirm": auto_confirm,
        }

    @staticmethod
    def _looks_like_new_plan(text: str) -> bool:
        return UserInteractionAgent._current_turn_intent(text)["requests_planning"]

    @staticmethod
    def _looks_like_auto_confirmed_replan(text: str) -> bool:
        normalized = re.sub(r"\s+", "", text or "").lower()
        if not normalized:
            return False
        confirm_terms = (
            "重新生成", "生成行程", "生成方案", "开始生成", "开始规划",
            "重新规划", "重做行程", "重新做行程", "重新排行程",
            "帮我规划", "帮我做行程", "帮我安排", "排行程", "做行程",
            "就按这个做", "就按照这个做", "按这个做", "按照这个做",
        )
        reference_execution = re.search(
            r"(?:就)?(?:按|按照|照|基于|根据)(?:这个|刚才|之前|上次|上一版)"
            r"(?:方案|配置|设置|条件|行程)?(?:做|来|规划|生成|重新规划|重新生成)",
            normalized,
        )
        fuzzy_replan = re.search(
            r"(?:重新|再|重做).{0,8}(?:生成|规划|排行程|做行程|安排)",
            normalized,
        )
        fuzzy_generate = re.search(
            r"帮我.{0,8}(?:生成|规划|安排|做).{0,4}(?:方案|行程|路线)",
            normalized,
        )
        return (
            any(term in normalized for term in confirm_terms)
            or bool(reference_execution)
            or bool(fuzzy_replan)
            or bool(fuzzy_generate)
        )

    @staticmethod
    def _looks_like_travel_generation_request(text: str) -> bool:
        normalized = re.sub(r"\s+", "", text or "").lower()
        if not normalized:
            return False
        if UserInteractionAgent._looks_like_auto_confirmed_replan(normalized):
            return True
        return bool(re.search(
            r"(?:生成|规划|安排|制作|做).{0,6}(?:旅行|旅游|行程|路线|方案)",
            normalized,
        ))

    @staticmethod
    def _assistant_promised_unstructured_plan(text: str) -> bool:
        if not text or CONFIRMATION_MARKER in text:
            return False
        normalized = re.sub(r"\s+", "", text).lower()
        return bool(re.search(
            r"(?:我现在就|马上|可以|就可以).{0,12}(?:生成|规划|做|安排).{0,8}(?:详细)?(?:行程|方案|路线)",
            normalized,
        ))

    @staticmethod
    def _has_active_planning_prompt(turns: list[dict]) -> bool:
        previous_turn = UserInteractionAgent._last_assistant_turn_before_current_user(turns)
        if not previous_turn:
            return False
        previous_assistant = str(previous_turn.get("content", ""))
        metadata = previous_turn.get("metadata")
        if isinstance(metadata, dict) and metadata.get("agent_status") in {
            "collecting",
            "awaiting_confirmation",
        }:
            return True
        if CONFIRMATION_MARKER in previous_assistant:
            current_user = UserInteractionAgent._last_user_text(turns)
            return (
                UserInteractionAgent._looks_positive(current_user)
                or UserInteractionAgent._looks_negative(current_user)
                or bool(re.search(
                    r"(改|换|调整|预算|出发|目的地|去|到|玩|天|日期|时间|菜系|口味|交通|步行|地铁|打车|自驾|偏好|喜欢|不喜欢|沿用)",
                    current_user,
                ))
            )
        markers = (
            "请告诉我你从哪个城市出发",
            "想去哪个目的地",
            "请告诉我具体出发日期",
            "这次计划玩几天",
            "这次旅行总预算大概是多少",
            "你有什么旅行偏好",
            "请补充出发地",
            "请补充目的地",
            "请补充出发日期",
            "请补充时长",
            "请补充预算",
            "请补充偏好",
        )
        return any(marker in previous_assistant for marker in markers)

    @staticmethod
    def _last_assistant_turn_before_current_user(turns: list[dict]) -> dict | None:
        seen_current_user = False
        for turn in reversed(turns):
            role = turn.get("role")
            if role == "user" and not seen_current_user:
                seen_current_user = True
                continue
            if seen_current_user and role == "assistant":
                return turn
        return None

    @staticmethod
    def _last_assistant_before_current_user(turns: list[dict]) -> str:
        seen_current_user = False
        for turn in reversed(turns):
            role = turn.get("role")
            if role == "user" and not seen_current_user:
                seen_current_user = True
                continue
            if seen_current_user and role == "assistant":
                return str(turn.get("content", ""))
        return ""

    @staticmethod
    def _scope_to_current_planning_run(turns: list[dict]) -> list[dict]:
        start_idx = 0
        for idx, turn in enumerate(turns):
            if turn.get("role") != "user":
                continue
            content = str(turn.get("content", ""))
            previous_assistant = UserInteractionAgent._last_assistant_before_index(turns, idx)
            if CONFIRMATION_MARKER in previous_assistant and UserInteractionAgent._looks_positive(content):
                continue
            if UserInteractionAgent._looks_like_new_plan(content):
                start_idx = idx
        return turns[start_idx:]

    @staticmethod
    def _last_assistant_before_index(turns: list[dict], index: int) -> str:
        for turn in reversed(turns[:index]):
            if turn.get("role") == "assistant":
                return str(turn.get("content", ""))
        return ""

    @staticmethod
    def _extract_reserve_budget(text: str) -> float:
        if not text:
            return 0.0
        normalized = re.sub(r"\s+", "", text)
        patterns = (
            r"(?:留|预留|留下|剩下)(?:¥|￥)?(\d+(?:\.\d+)?)(?:元|块)?(?:作为)?(?:应急|备用|机动)",
            r"(?:应急|备用|机动)(?:金|预算)?(?:¥|￥)?(\d+(?:\.\d+)?)(?:元|块)?",
        )
        for pattern in patterns:
            match = re.search(pattern, normalized)
            if match:
                return float(match.group(1))
        return 0.0

    @staticmethod
    def _apply_inherited_fields(
        extracted: dict[str, Any],
        full_turns: list[dict],
        current_user: str,
        context: dict[str, Any] | None = None,
        turn_intent: dict[str, bool] | None = None,
    ) -> dict[str, Any]:
        text = current_user or ""
        turn_intent = turn_intent or UserInteractionAgent._current_turn_intent(text)

        # 目的地变更直接覆盖
        destination_change = UserInteractionAgent._extract_destination_change(text)
        if destination_change:
            extracted["destination"] = destination_change

        previous = UserInteractionAgent._merge_trip_data(
            UserInteractionAgent._latest_trip_from_context(context or {}),
            UserInteractionAgent._latest_confirmed_trip(full_turns),
        )
        if not previous:
            return extracted

        full_config = turn_intent["inherits_previous_config"]

        # 继承核心字段
        UserInteractionAgent._inherit_core_fields(extracted, previous, full_config)
        # 继承日期并丢弃需要重新推导的旧值
        UserInteractionAgent._inherit_dates(extracted, previous, text, full_config)
        # 继承预算
        UserInteractionAgent._inherit_budget(extracted, previous, text, full_config)
        # 旅行偏好与菜系偏好分别继承
        UserInteractionAgent._inherit_preferences(extracted, previous, text, full_config)
        UserInteractionAgent._inherit_cuisine_preferences(
            extracted, previous, text, full_config,
        )
        # 继承其他配置
        UserInteractionAgent._inherit_config_fields(extracted, previous, text, full_config)

        return extracted

    @staticmethod
    def _inherit_core_fields(extracted: dict, previous: dict, full_config: bool) -> None:
        if not full_config:
            return
        for field in ("destination", "origin"):
            if not extracted.get(field) and previous.get(field):
                extracted[field] = previous[field]

    @staticmethod
    def _inherit_dates(
        extracted: dict,
        previous: dict,
        text: str,
        full_config: bool,
    ) -> None:
        if not full_config:
            return

        mentions_dates = UserInteractionAgent._mentions_field_override(text, "trip_dates")
        mentions_days = UserInteractionAgent._mentions_field_override(text, "days")
        has_start = mentions_dates and bool(extracted.get("start_date"))
        has_end = mentions_dates and bool(extracted.get("end_date"))
        has_days = (mentions_dates or mentions_days) and int(extracted.get("days") or 0) > 0

        if not has_start and not has_end and not has_days:
            extracted["start_date"] = previous.get("start_date", "")
            extracted["end_date"] = previous.get("end_date", "")
            extracted["days"] = previous.get("days", 0)
            return

        if not has_start:
            extracted["start_date"] = previous.get("start_date", "")
        if has_start and not has_end and not has_days:
            extracted["days"] = previous.get("days", 0)
        elif has_days and not has_start and not has_end:
            extracted["start_date"] = previous.get("start_date", "")

        if has_end and not has_days:
            extracted["days"] = 0
        if has_days and not has_end:
            extracted["end_date"] = ""

    @staticmethod
    def _inherit_budget(extracted: dict, previous: dict, text: str, full_config: bool) -> None:
        if not (full_config or re.search(r"沿用上次(?:的)?预算|预算(?:沿用|照旧|不变)", text)):
            return
        if UserInteractionAgent._mentions_field_override(text, "budget"):
            return
        extracted["total_budget"] = extracted.get("total_budget") or previous.get("total_budget", 0)
        extracted["reserve_budget"] = previous.get("reserve_budget", extracted.get("reserve_budget", 0))
        extracted["planning_budget"] = (
            extracted.get("planning_budget")
            or previous.get("planning_budget")
            or max(float(extracted.get("total_budget") or 0)
                    - float(extracted.get("reserve_budget") or 0), 0.0)
        )

    @staticmethod
    def _inherit_preferences(extracted: dict, previous: dict, text: str, full_config: bool) -> None:
        if not (full_config or re.search(r"沿用上次(?:的)?偏好|偏好(?:沿用|照旧|不变)", text)):
            return
        if UserInteractionAgent._mentions_field_override(text, "preferences"):
            return
        extracted["preferences"] = extracted.get("preferences") or previous.get("preferences", [])
        extracted["preferences_provided"] = bool(
            previous.get("preferences_provided", True) or extracted.get("preferences"))

    @staticmethod
    def _inherit_cuisine_preferences(
        extracted: dict,
        previous: dict,
        text: str,
        full_config: bool,
    ) -> None:
        if not (
            full_config
            or re.search(r"沿用上次(?:的)?(?:菜系|口味)|(?:菜系|口味)(?:沿用|照旧|不变)", text)
        ):
            return
        if UserInteractionAgent._mentions_field_override(text, "cuisine_preferences"):
            return
        extracted["cuisine_preferences"] = previous.get("cuisine_preferences", [])
        extracted["preferences_provided"] = bool(
            previous.get("preferences_provided", True)
            or extracted.get("preferences")
            or extracted.get("cuisine_preferences")
        )

    @staticmethod
    def _inherit_config_fields(extracted: dict, previous: dict, text: str, full_config: bool) -> None:
        if not full_config:
            return
        for field in (
            "pace", "hotel_star", "hotel_budget", "meal_budget", "travelers",
            "preferred_transport",
        ):
            if field in previous and not UserInteractionAgent._mentions_field_override(text, field):
                extracted[field] = previous[field]

    @staticmethod
    def _extract_destination_change(text: str) -> str:
        normalized = re.sub(r"\s+", "", text or "")
        if not normalized:
            return ""
        patterns = (
            r"(?:目的地|旅行地|旅游地|终点).{0,4}(?:变成|改成|换成|改为|换为|换到|改到|改去|换去|改)([^，,。；;！？!?]+)",
            r"(?:换成|改成|换到|改到|改去|换去|改为|换为)([^，,。；;！？!?]+)",
            r"换(?!个|一下|预算|时间|天数|偏好|住宿|酒店)([^，,。；;！？!?]+)",
            r"(?:想要去|想改去|又想去|还想去|现在想去|想去|去|到)([^，,。；;！？!?]+)",
        )
        for pattern in patterns:
            match = re.search(pattern, normalized)
            if not match:
                continue
            destination = UserInteractionAgent._clean_destination_candidate(match.group(1))
            if destination:
                return destination
        return ""

    @staticmethod
    def _clean_destination_candidate(text: str) -> str:
        destination = re.split(
            r"(?:(?:其(?:还|还是|也|都)?(?:一样|相同|不变|照旧))|"
            r"其他|其它|其余|剩下的|剩下|别的|沿用|照旧|不变|相同|一样|"
            r"配置|设置|条件|方案|行程|路线|帮我|重新|再|预算|总预算|时间|天数|"
            r"偏好|喜欢|确认|可以|行吗|好吗|吗|呢|么|周末游|周末|玩|旅游|旅行|游|"
            r"\d+天|[一二两三四五六七八九十]+天)",
            text,
            maxsplit=1,
        )[0]
        destination = destination.strip("，,。；;！？!? ")
        destination = re.sub(r"(?:的|吧|呀|啊|哦|啦|了|呢|哈|嘛)+$", "", destination)
        destination = destination.strip("，,。；;！？!? ")
        invalid = {
            "",
            "哪里",
            "哪儿",
            "哪",
            "这里",
            "那里",
            "这个",
            "那个",
            "什么地方",
            "地方",
            "个地方",
            "一下",
        }
        if destination in invalid or len(destination) > 20:
            return ""
        return destination

    @staticmethod
    def _looks_like_full_config_inheritance(text: str) -> bool:
        normalized = re.sub(r"\s+", "", text or "").lower()
        other = r"(?:其|其他|其它|其余|剩下的|别的)(?:部分|内容|安排|配置|设置|条件|行程)?"
        previous = r"(?:上次|之前|此前|刚才|前面|原来|原先|上一版|这个)"
        same = r"(?:一样|相同|不变|照旧|沿用)"
        patterns = (
            rf"{other}(?:都|全部|全都)?(?:和|跟|同){previous}(?:的)?{same}",
            rf"{other}(?:还|还是|也|都|全部|全都)?{same}(?:{previous})?(?:的)?(?:配置|设置|条件|安排|行程)?",
            rf"{other}(?:都|全部|全都)?(?:沿用|照旧)(?:{previous}|相同|同样)?(?:的)?(?:配置|设置|条件|安排|行程)?",
            rf"(?:沿用|照旧){previous}(?:的)?(?:配置|设置|条件|安排|行程)",
            r"(?:相同|同样)(?:配置|设置|条件)",
            r"配置(?:沿用|照旧|不变)",
            rf"(?:按|按照|照|基于|根据){previous}(?:方案|配置|设置|条件|行程)?"
            r"(?:重新|重做|生成|规划|做|来)",
        )
        return any(re.search(pattern, normalized) for pattern in patterns)

    @staticmethod
    def _mentions_field_override(text: str, field: str) -> bool:
        normalized = re.sub(r"\s+", "", text or "")
        patterns = {
            "budget": r"(?:预算|总预算).{0,8}(?:¥|￥|\d|不限)|(?:¥|￥)\d|\d+(?:元|块)",
            "preferences": (
                r"(?:喜欢(?!吃)|想看|不喜欢(?!吃)|无偏好|没有偏好|没偏好|随便|"
                r"都可以|都行|不限偏好|偏好(?:是|为|改成|换成|设为|[:：]))"
            ),
            "cuisine_preferences": (
                r"(?:菜系|口味|饮食|想吃|喜欢吃|不吃|忌口|素食|清真|川菜|粤菜|"
                r"湘菜|鲁菜|淮扬菜|西餐|日料|韩餐)"
            ),
            "pace": r"(?:节奏|轻松|慢游|适中|紧凑)",
            "preferred_transport": (
                r"(?:交通方式|出行方式|地铁|公交|公共交通|步行|自驾|打车)"
            ),
            "hotel_star": r"(?:星级|\d星|[一二三四五六七八九十]星|三星|四星|五星)",
            "hotel_budget": r"(?:酒店|住宿|每晚|房费|住宿预算).{0,8}(?:¥|￥|\d|不限)",
            "meal_budget": r"(?:餐饮|吃饭|饭钱|餐标|人均).{0,8}(?:¥|￥|\d|不限)",
            "travelers": r"(?:\d+人|一个人|两个人|三个人|人数|旅客|游客)",
            "preferred_transport": r"(?:交通|步行|走路|徒步|地铁|公交|巴士|打车|出租|网约车|自驾|开车)",
            "trip_dates": (
                r"(?:出发日期|返程日期|日期|时间|出发|返程|结束|"
                r"\d{4}-\d{1,2}-\d{1,2}|\d{1,2}月\d{1,2}日|"
                r"今天|明天|后天|下周|下个月)"
            ),
            "days": r"(?:玩|游|行程|改成|调整为)?\d+天|[一二两三四五六七八九十]+天",
        }
        return bool(re.search(patterns.get(field, r"$^"), normalized))

    @staticmethod
    def _merge_trip_data(primary: dict[str, Any], secondary: dict[str, Any]) -> dict[str, Any]:
        merged = dict(primary or {})
        for key, value in (secondary or {}).items():
            if UserInteractionAgent._trip_value_present(key, value):
                merged[key] = value
        return merged

    @staticmethod
    def _trip_value_present(field: str, value: Any) -> bool:
        if field in {"preferences", "cuisine_preferences"}:
            return isinstance(value, list)
        if field in {"preferences_provided", "preferred_transport_provided"}:
            return isinstance(value, bool)
        if field in {"origin", "destination", "start_date", "end_date", "pace", "preferred_transport"}:
            return bool(UserInteractionAgent._to_str(value))
        if field in {
            "days", "total_budget", "planning_budget", "hotel_star",
            "hotel_budget", "meal_budget", "travelers",
        }:
            return UserInteractionAgent._to_float(value) > 0
        if field == "reserve_budget":
            return value is not None
        return value not in (None, "")

    @staticmethod
    def _latest_trip_from_context(context: dict[str, Any]) -> dict[str, Any]:
        summary = context.get("latest_plan_summary")
        if not isinstance(summary, dict):
            return {}
        trip_config = summary.get("trip_config") if isinstance(summary.get("trip_config"), dict) else {}
        budget = (
            trip_config.get("budget")
            if isinstance(trip_config.get("budget"), dict)
            else summary.get("budget") if isinstance(summary.get("budget"), dict) else {}
        )
        return {
            "destination": UserInteractionAgent._to_str(
                trip_config.get("destination") or summary.get("destination")
            ),
            "origin": UserInteractionAgent._to_str(
                trip_config.get("origin") or summary.get("origin")
            ),
            "days": UserInteractionAgent._to_int(
                trip_config.get("days") or summary.get("days")
            ),
            "start_date": UserInteractionAgent._to_str(
                UserInteractionAgent._config_or_summary(
                    trip_config, summary, "start_date",
                )
            ),
            "end_date": UserInteractionAgent._to_str(
                UserInteractionAgent._config_or_summary(
                    trip_config, summary, "end_date",
                )
            ),
            "total_budget": UserInteractionAgent._to_float(
                budget.get("total_budget") or trip_config.get("total_budget") or summary.get("total_budget")
            ),
            "reserve_budget": UserInteractionAgent._to_float(
                budget.get("reserve_budget") or trip_config.get("reserve_budget") or summary.get("reserve_budget")
            ),
            "planning_budget": UserInteractionAgent._to_float(
                budget.get("planning_budget") or trip_config.get("planning_budget") or summary.get("planning_budget")
            ),
            "preferences": UserInteractionAgent._normalize_preferences(
                trip_config.get("preferences") if "preferences" in trip_config else summary.get("preferences")
            ),
            "cuisine_preferences": UserInteractionAgent._normalize_preferences(
                trip_config.get("cuisine_preferences")
                if "cuisine_preferences" in trip_config
                else summary.get("cuisine_preferences")
            ),
            "preferences_provided": UserInteractionAgent._to_bool(
                trip_config.get("preferences_provided")
                if "preferences_provided" in trip_config
                else summary.get("preferences_provided", "preferences" in summary)
            ),
            "cuisine_preferences": UserInteractionAgent._normalize_preferences(
                UserInteractionAgent._config_or_summary(
                    trip_config, summary, "cuisine_preferences",
                )
            ),
            "preferred_transport": UserInteractionAgent._to_str(
                UserInteractionAgent._config_or_summary(
                    trip_config, summary, "preferred_transport",
                )
            ),
            "preferred_transport_provided": UserInteractionAgent._to_bool(
                UserInteractionAgent._config_or_summary(
                    trip_config, summary, "preferred_transport_provided",
                )
            ),
            "pace": UserInteractionAgent._to_str(trip_config.get("pace") or summary.get("pace")),
            "preferred_transport": UserInteractionAgent._to_str(
                trip_config.get("preferred_transport")
                or summary.get("preferred_transport")
            ),
            "hotel_star": UserInteractionAgent._to_int(trip_config.get("hotel_star") or summary.get("hotel_star")),
            "hotel_budget": UserInteractionAgent._to_float(
                trip_config.get("hotel_budget") or summary.get("hotel_budget")
            ),
            "meal_budget": UserInteractionAgent._to_float(
                trip_config.get("meal_budget") or summary.get("meal_budget")
            ),
            "travelers": UserInteractionAgent._to_int(trip_config.get("travelers") or summary.get("travelers")),
        }

    @staticmethod
    def _config_or_summary(trip_config: dict, summary: dict, field: str) -> Any:
        if field in trip_config:
            return trip_config.get(field)
        return summary.get(field)

    @staticmethod
    def _latest_plan_summary_text(context: dict[str, Any]) -> str:
        summary = context.get("latest_plan_summary")
        if not isinstance(summary, dict):
            return ""
        parts = []
        origin = UserInteractionAgent._to_str(summary.get("origin"))
        destination = UserInteractionAgent._to_str(summary.get("destination"))
        days = UserInteractionAgent._to_int(summary.get("days"))
        trip_config = summary.get("trip_config") if isinstance(summary.get("trip_config"), dict) else {}
        if trip_config:
            origin = origin or UserInteractionAgent._to_str(trip_config.get("origin"))
            destination = destination or UserInteractionAgent._to_str(trip_config.get("destination"))
            days = days or UserInteractionAgent._to_int(trip_config.get("days"))
        if origin and destination:
            parts.append(f"{origin}到{destination}")
        elif destination:
            parts.append(f"目的地{destination}")
        if days > 0:
            parts.append(f"{days}天")
        start_date = UserInteractionAgent._to_str(
            UserInteractionAgent._config_or_summary(
                trip_config, summary, "start_date",
            )
        )
        end_date = UserInteractionAgent._to_str(
            UserInteractionAgent._config_or_summary(
                trip_config, summary, "end_date",
            )
        )
        if start_date and end_date:
            parts.append(f"日期{start_date}至{end_date}")

        trip_budget = trip_config.get("budget") if isinstance(trip_config.get("budget"), dict) else {}
        budget = summary.get("budget") if isinstance(summary.get("budget"), dict) else trip_budget
        total_budget = UserInteractionAgent._to_float(
            budget.get("total_budget") or trip_config.get("total_budget") or summary.get("total_budget")
        )
        planning_budget = UserInteractionAgent._to_float(
            budget.get("planning_budget") or trip_config.get("planning_budget") or summary.get("planning_budget")
        )
        reserve_budget = UserInteractionAgent._to_float(
            budget.get("reserve_budget") or trip_config.get("reserve_budget") or summary.get("reserve_budget")
        )
        if total_budget > 0:
            budget_text = f"总预算¥{UserInteractionAgent._format_number(total_budget)}"
            if reserve_budget > 0:
                budget_text += f"，应急¥{UserInteractionAgent._format_number(reserve_budget)}"
            if planning_budget > 0 and planning_budget != total_budget:
                budget_text += f"，规划预算¥{UserInteractionAgent._format_number(planning_budget)}"
            parts.append(budget_text)

        preferences = UserInteractionAgent._normalize_preferences(
            trip_config.get("preferences") if "preferences" in trip_config else summary.get("preferences")
        )
        if preferences:
            parts.append(f"偏好{'、'.join(preferences)}")
        cuisine_preferences = UserInteractionAgent._normalize_preferences(
            UserInteractionAgent._config_or_summary(
                trip_config, summary, "cuisine_preferences",
            )
        )
        if cuisine_preferences:
            parts.append(f"菜系{'、'.join(cuisine_preferences)}")
        preferred_transport = UserInteractionAgent._to_str(
            UserInteractionAgent._config_or_summary(
                trip_config, summary, "preferred_transport",
            )
        )
        if preferred_transport:
            parts.append(f"交通{preferred_transport}")
        return "，".join(parts)

    @staticmethod
    def _latest_confirmed_trip(turns: list[dict]) -> dict[str, Any]:
        for turn in reversed(turns):
            content = str(turn.get("content", ""))
            if turn.get("role") != "assistant" or CONFIRMATION_MARKER not in content:
                continue
            total_budget = 0.0
            reserve_budget = 0.0
            planning_budget = 0.0
            budget_match = re.search(r"(?:预算|总预算)\s*¥?(\d+(?:\.\d+)?)", content)
            if budget_match:
                total_budget = float(budget_match.group(1))
            reserve_match = re.search(r"¥?(\d+(?:\.\d+)?)\s*留作应急", content)
            if reserve_match:
                reserve_budget = float(reserve_match.group(1))
            planning_match = re.search(r"按\s*¥?(\d+(?:\.\d+)?)\s*安排", content)
            if planning_match:
                planning_budget = float(planning_match.group(1))
            elif total_budget > 0:
                planning_budget = max(total_budget - reserve_budget, 0.0)

            preferences = []
            preferences_provided = False
            pref_match = re.search(r"偏好\s*([^，,。]+)", content)
            if pref_match:
                preferences_provided = True
                pref_text = pref_match.group(1).replace(CONFIRMATION_MARKER, "").strip("，, ")
                if pref_text and not UserInteractionAgent._mentions_no_preference(pref_text):
                    preferences = [item.strip() for item in re.split(r"、|,|，", pref_text) if item.strip()]

            cuisine_preferences = []
            cuisine_match = re.search(r"菜系\s*([^，,。]+)", content)
            if cuisine_match:
                cuisine_text = cuisine_match.group(1).replace(CONFIRMATION_MARKER, "").strip("，, ")
                if cuisine_text and cuisine_text != "无":
                    cuisine_preferences = [
                        item.strip()
                        for item in re.split(r"、|,|，", cuisine_text)
                        if item.strip()
                    ]
                    preferences_provided = True

            transport = ""
            preferred_transport_provided = False
            transport_match = re.search(r"交通\s*([^，,。]+)", content)
            if transport_match:
                transport = UserInteractionAgent._normalize_transport(transport_match.group(1))
                preferred_transport_provided = True

            date_match = re.search(
                r"日期\s*(\d{4}-\d{2}-\d{2})\s*至\s*(\d{4}-\d{2}-\d{2})",
                content,
            )
            start_date = date_match.group(1) if date_match else ""
            end_date = date_match.group(2) if date_match else ""

            route_match = re.search(
                r"从\s*([^，,。]+?)\s*出发，?\s*去\s*([^，,。]+?)[，,。].*?玩\s*(\d+)\s*天",
                content,
            )
            origin = route_match.group(1).strip() if route_match else ""
            destination = route_match.group(2).strip() if route_match else ""
            days = int(route_match.group(3)) if route_match else 0

            confirmed_trip = {
                "origin": origin,
                "destination": destination,
                "start_date": start_date,
                "end_date": end_date,
                "days": days,
                "total_budget": total_budget,
                "reserve_budget": reserve_budget,
                "planning_budget": planning_budget,
                "preferences": preferences,
                "preferred_transport": transport,
                "preferred_transport_provided": preferred_transport_provided,
                "preferences_provided": preferences_provided,
            }
            if cuisine_match:
                confirmed_trip["cuisine_preferences"] = cuisine_preferences
            return confirmed_trip
        return {}
