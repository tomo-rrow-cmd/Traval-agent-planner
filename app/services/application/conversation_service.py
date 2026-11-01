"""对话服务 — DB 持久化"""

from datetime import date, timedelta

from app.db.repositories.plan_repo import PlanRepository
from app.db.session import async_session_factory
from app.db.repositories.conversation_repo import ConversationRepository
from app.exceptions import BadRequestException, NotFoundException
from app.schemas.chat import (
    ChatMessageCreateRequest,
    ChatSession,
    ChatSessionCreateRequest,
    ChatSessionUpdateRequest,
    ConversationPlanRunRecord,
    MessageRecord,
)
from app.schemas.common import CursorPaginatedData, PaginatedData
from app.services.application.plan_result_message import (
    PLAN_RESULT_FORMAT,
    build_plan_result_message,
)

DEFAULT_SESSION_TITLE = "新的旅行规划"
PLACEHOLDER_SESSION_TITLES = frozenset({DEFAULT_SESSION_TITLE, "新对话"})


class ConversationService:

    @staticmethod
    def _session_response(conv, message_count: int = 0,
                          last_message_preview: str | None = None,
                          session_title: str | None = None) -> ChatSession:
        return ChatSession(
            id=conv.id,
            title=session_title if session_title is not None else conv.title,
            status=conv.status,
            message_count=message_count, pinned=bool(getattr(conv, "pinned", False)),
            plan_run_id=getattr(conv, "plan_id", None),
            last_message_preview=last_message_preview,
            created_at=conv.created_at, updated_at=conv.updated_at,
        )

    @staticmethod
    def _title_from_message(content: str | None) -> str:
        normalized = " ".join((content or "").split())
        return normalized[:20] + ("…" if len(normalized) > 20 else "")

    @classmethod
    def _resolved_session_title(cls, conv, first_user_message: str | None) -> str:
        current_title = str(getattr(conv, "title", "") or "")
        if current_title.strip() not in PLACEHOLDER_SESSION_TITLES:
            return current_title
        return cls._title_from_message(first_user_message) or current_title or DEFAULT_SESSION_TITLE

    @staticmethod
    def _message_response(message, session_id: str,
                          summary: dict | None = None) -> MessageRecord:
        metadata = dict(message.metadata_json or {})
        if summary is not None:
            metadata["summary"] = summary
        return MessageRecord(
            id=message.id, session_id=session_id, role=message.role,
            content=message.content, message_type=message.message_type or "text",
            metadata=metadata, created_at=message.created_at,
        )

    async def _owned_session(self, repo: ConversationRepository, user_id: str,
                             session_id: str):
        conv = await repo.get(session_id, user_id=user_id)
        if conv is None:
            raise NotFoundException("Chat session not found")
        return conv

    async def create_session(self, user_id: str, request: ChatSessionCreateRequest) -> ChatSession:
        async with async_session_factory() as db:
            repo = ConversationRepository(db)
            conv = await repo.create(user_id=user_id, title=request.title or DEFAULT_SESSION_TITLE)
            await db.commit()
            return self._session_response(conv)

    async def list_sessions(self, user_id: str, page=1, page_size=20) -> PaginatedData[ChatSession]:
        async with async_session_factory() as db:
            repo = ConversationRepository(db)
            rows, total = await repo.list_by_user(
                user_id=user_id, offset=(page - 1) * page_size, limit=page_size,
            )
            sessions = []
            for row in rows:
                if isinstance(row, tuple) or hasattr(row, "_mapping"):
                    values = tuple(row)
                    conv = values[0]
                    message_count = values[1] if len(values) > 1 else 0
                    preview = values[2] if len(values) > 2 else None
                    first_user_message = values[3] if len(values) > 3 else None
                else:
                    conv, message_count, preview = row, 0, None
                    first_user_message = None
                sessions.append(self._session_response(
                    conv,
                    message_count,
                    preview,
                    self._resolved_session_title(conv, first_user_message),
                ))
            return PaginatedData.create(
                sessions, total=total, page=page, page_size=page_size,
            )

    async def merge_sessions(self, source_user_id: str, target_user_id: str) -> int:
        if not source_user_id or not target_user_id or source_user_id == target_user_id:
            return 0
        async with async_session_factory() as db:
            repo = ConversationRepository(db)
            merged_count = await repo.reassign_user(source_user_id, target_user_id)
            await db.commit()
            return merged_count

    async def update_session(self, user_id: str, session_id: str,
                             request: ChatSessionUpdateRequest) -> ChatSession:
        async with async_session_factory() as db:
            repo = ConversationRepository(db)
            conv = await self._owned_session(repo, user_id, session_id)
            await repo.update_session(conv, title=request.title, pinned=request.pinned)
            await db.commit()
            return self._session_response(conv)

    async def delete_session(self, user_id: str, session_id: str) -> dict:
        async with async_session_factory() as db:
            repo = ConversationRepository(db)
            await self._owned_session(repo, user_id, session_id)
            await repo.update_status(session_id, "archived", user_id=user_id)
            await db.commit()
        return {}

    async def record_message(self, user_id: str, session_id: str,
                             request: ChatMessageCreateRequest) -> tuple[MessageRecord, bool]:
        async with async_session_factory() as db:
            repo = ConversationRepository(db)
            conv = await self._owned_session(repo, user_id, session_id)
            # 将图片 URL 存入消息 metadata
            metadata = {"images": request.images} if request.images else None
            message = await repo.add_message(
                session_id, "user", request.content,
                client_message_id=request.client_message_id,
                metadata_json=metadata,
            )
            replayed = bool(getattr(message, "_idempotent_replay", False))
            if not replayed:
                conv.updated_at = message.created_at
                if str(conv.title or "").strip() in PLACEHOLDER_SESSION_TITLES:
                    conv.title = self._title_from_message(request.content)
            await db.commit()
            return self._message_response(message, session_id), not replayed

    async def record_ai_reply(
        self,
        session_id: str,
        content: str,
        user_id: str | None = None,
        metadata: dict | None = None,
    ):
        async with async_session_factory() as db:
            repo = ConversationRepository(db)
            conv = None
            if user_id:
                conv = await self._owned_session(repo, user_id, session_id)
            message = await repo.add_message(
                session_id,
                "assistant",
                content,
                metadata_json=metadata,
            )
            if conv is not None:
                conv.updated_at = message.created_at
            await db.commit()

    async def get_session_context(self, user_id: str, session_id: str) -> dict:
        async with async_session_factory() as db:
            repo = ConversationRepository(db)
            conv = await self._owned_session(repo, user_id, session_id)
            runs = await repo.list_plan_runs(session_id)
            return {
                "session_status": conv.status,
                "latest_plan_id": conv.plan_id,
                "latest_plan_summary": runs[0].summary if runs else {},
                "has_completed_plan": bool(runs) or conv.status == "completed",
                "plan_run_count": len(runs),
            }

    async def persist_plan_result(
        self,
        user_id: str,
        session_id: str,
        summary: dict,
    ) -> ConversationPlanRunRecord:
        import logging
        log = logging.getLogger(__name__)

        destination = str(summary.get("destination") or "")
        days = int(summary.get("days") or 0)
        try:
            async with async_session_factory() as db:
                repo = ConversationRepository(db)

                log.info("[N6.step1] checking _owned_session...")
                await self._owned_session(repo, user_id, session_id)
                log.info("[N6.step1] OK")

                log.info("[N6.step2] creating plan_run...")
                run = await repo.create_plan_run(
                    conv_id=session_id,
                    destination=destination,
                    days=days,
                    summary=summary,
                )
                log.info("[N6.step2] OK run_id=%s", run.id)

                log.info("[N6.step3] updating session status to completed...")
                await repo.update_status(
                    session_id,
                    "completed",
                    plan_id=run.id,
                    destination=destination,
                    days=days,
                    user_id=user_id,
                )
                log.info("[N6.step3] OK")

                log.info("[N6.step4] generating compact result message...")
                message_content = build_plan_result_message(summary)
                log.info("[N6.step4] OK length=%d", len(message_content))

                log.info("[N6.step5] adding plan_result message...")
                await repo.add_message(
                    session_id, "assistant", message_content,
                    message_type="plan_result",
                    metadata_json={
                        "plan_run_id": run.id,
                        "plan_id": run.id,
                        "summary": summary,
                        "result_format": PLAN_RESULT_FORMAT,
                    },
                    client_message_id=f"plan-result:{run.id}",
                )
                log.info("[N6.step5] OK")

                log.info("[N6.step6] committing core result transaction...")
                await db.commit()
                log.info("[N6.step6] OK")

                record = ConversationPlanRunRecord(
                    id=run.id,
                    destination=run.destination or "",
                    days=run.days or 0,
                    summary=run.summary or {},
                    created_at=run.created_at,
                )
        except Exception:
            log.exception("[N6.FATAL] core plan result persistence failed")
            raise

        await self._sync_plan_record(
            user_id=user_id,
            run_id=record.id,
            summary=summary,
            destination=destination,
            days=days,
        )
        return record

    async def _sync_plan_record(
        self,
        *,
        user_id: str,
        run_id: str,
        summary: dict,
        destination: str,
        days: int,
    ) -> None:
        import logging
        from sqlalchemy import text

        log = logging.getLogger(__name__)
        try:
            async with async_session_factory() as db:
                user_ok = await db.execute(
                    text("SELECT 1 FROM users WHERE id = :uid"),
                    {"uid": user_id},
                )
                if not user_ok.scalar():
                    log.info("[N6.plan] SKIP (user %s not in users table)", user_id)
                    return

                budget_data = summary.get("budget")
                budget_data = budget_data if isinstance(budget_data, dict) else {}
                trip_config = summary.get("trip_config")
                trip_config = trip_config if isinstance(trip_config, dict) else {}
                budget = float(
                    summary.get("total_budget")
                    or budget_data.get("total_budget")
                    or 0
                )
                travelers = int(
                    summary.get("travelers")
                    or trip_config.get("travelers")
                    or 1
                )
                start_date = date.today()
                end_date = start_date + timedelta(days=max(days - 1, 0))
                plan = await PlanRepository(db).upsert_plan_from_summary(
                    user_id=user_id,
                    plan_id=run_id,
                    summary=summary,
                    destination=destination,
                    start_date=start_date,
                    end_date=end_date,
                    budget=budget,
                    travelers=travelers,
                )
                await db.commit()
                log.info("[N6.plan] OK plan_id=%s", plan.id)
        except Exception:
            log.exception("[N6.plan] optional plans table sync failed")

    async def get_plan_run(self, plan_run_id: str) -> dict | None:
        """按 plan_run_id 查询单条方案运行记录（SSE 管道生成）。"""
        async with async_session_factory() as db:
            repo = ConversationRepository(db)
            run = await repo.get_plan_run(plan_run_id)
            if not run:
                return None
            return {
                "id": run.id,
                "summary": run.summary or {},
                "destination": run.destination or "",
                "days": run.days or 0,
            }

    async def list_plan_runs(
        self,
        user_id: str,
        session_id: str,
    ) -> list[ConversationPlanRunRecord]:
        async with async_session_factory() as db:
            repo = ConversationRepository(db)
            await self._owned_session(repo, user_id, session_id)
            runs = await repo.list_plan_runs(session_id)
            return [
                ConversationPlanRunRecord(
                    id=run.id,
                    destination=run.destination or "",
                    days=run.days or 0,
                    summary=run.summary or {},
                    created_at=run.created_at,
                )
                for run in runs
            ]

    async def get_messages(self, user_id: str, session_id: str,
                           page=None, page_size=50, before_id=None, after_id=None, limit=50):
        if before_id and after_id:
            raise BadRequestException("before_id and after_id cannot be used together")
        if page is not None and (before_id or after_id):
            raise BadRequestException("page and cursor parameters cannot be used together")

        async with async_session_factory() as db:
            repo = ConversationRepository(db)
            await self._owned_session(repo, user_id, session_id)
            if before_id or after_id:
                cursor_result = await repo.get_messages_cursor(
                    session_id, before_id=before_id, after_id=after_id, limit=limit,
                )
                if cursor_result is None:
                    raise BadRequestException("Message cursor not found in this session")
                messages, has_more = cursor_result
                records = await self._hydrate_messages(repo, session_id, messages)
                return CursorPaginatedData(
                    list=records, has_more=has_more,
                    next_before_id=(
                        records[0].id if before_id and has_more and records else None
                    ),
                    next_after_id=(
                        records[-1].id if after_id and has_more and records else None
                    ),
                )
            current_page = page or 1
            messages, total = await repo.get_messages_page(session_id, current_page, page_size)
            records = await self._hydrate_messages(repo, session_id, messages)
            return PaginatedData.create(
                records, total=total, page=current_page, page_size=page_size,
            )

    async def _hydrate_messages(self, repo: ConversationRepository, session_id: str,
                                messages: list) -> list[MessageRecord]:
        run_ids = {
            str((message.metadata_json or {}).get("plan_run_id"))
            for message in messages
            if (message.metadata_json or {}).get("plan_run_id")
        }
        runs = await repo.get_plan_runs_by_ids(session_id, run_ids)
        return [
            self._message_response(
                message, session_id,
                summary=runs[run_id].summary or {} if run_id in runs else None,
            )
            for message in messages
            for run_id in [str((message.metadata_json or {}).get("plan_run_id") or "")]
        ]
