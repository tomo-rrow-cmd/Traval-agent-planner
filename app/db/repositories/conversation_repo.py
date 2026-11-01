"""
对话历史 Repository — 持久化会话和消息
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.conversation import Conversation, ConversationPlanRun, Message


class ConversationRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: str = "", title: str = "",
                     destination: str = "", days: int = 0) -> Conversation:
        conv = Conversation(
            user_id=user_id or None,
            title=title or f"旅行规划 {datetime.utcnow().strftime('%m-%d %H:%M')}",
            destination=destination, days=days,
        )
        self.db.add(conv)
        await self.db.flush()
        return conv

    async def get(self, conv_id: str, user_id: str | None = None) -> Optional[Conversation]:
        query = select(Conversation).where(Conversation.id == conv_id)
        if user_id:
            query = query.where(Conversation.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: str = "", offset: int = 0,
                           limit: int = 20) -> tuple[list[tuple], int]:
        message_count = (
            select(func.count(Message.id))
            .where(Message.conversation_id == Conversation.id)
            .correlate(Conversation).scalar_subquery()
        )
        last_preview = (
            select(func.substr(Message.content, 1, 120))
            .where(Message.conversation_id == Conversation.id)
            .order_by(Message.sequence.desc()).limit(1)
            .correlate(Conversation).scalar_subquery()
        )
        first_user_message = (
            select(Message.content)
            .where(
                Message.conversation_id == Conversation.id,
                Message.role == "user",
            )
            .order_by(Message.sequence.asc()).limit(1)
            .correlate(Conversation).scalar_subquery()
        )
        query = select(
            Conversation,
            message_count,
            last_preview,
            first_user_message,
        ).where(
            Conversation.status != "archived"
        )
        count_query = select(func.count()).select_from(Conversation).where(
            Conversation.status != "archived"
        )
        if user_id:
            query = query.where(Conversation.user_id == user_id)
            count_query = count_query.where(Conversation.user_id == user_id)
        query = query.order_by(
            Conversation.pinned.desc(), Conversation.updated_at.desc()
        ).offset(offset).limit(limit)
        result = await self.db.execute(query)
        total = (await self.db.execute(count_query)).scalar_one()
        return list(result.all()), total

    async def lock_conversation(self, conv_id: str) -> Conversation | None:
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conv_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def update_session(self, conv: Conversation, *, title: str | None = None,
                             pinned: bool | None = None) -> Conversation:
        if title is not None:
            conv.title = title
        if pinned is not None:
            conv.pinned = pinned
        await self.db.flush()
        return conv

    async def update_status(self, conv_id: str, status: str, plan_id: str = "",
                            destination: str = "", days: int = 0,
                            user_id: str | None = None):
        conv = await self.get(conv_id, user_id=user_id)
        if conv:
            conv.status = status
            if plan_id:
                conv.plan_id = plan_id
            if destination:
                conv.destination = destination
            if days:
                conv.days = days
            await self.db.flush()

    async def reassign_user(self, source_user_id: str, target_user_id: str) -> int:
        result = await self.db.execute(
            update(Conversation)
            .where(Conversation.user_id == source_user_id)
            .values(user_id=target_user_id)
        )
        await self.db.flush()
        return int(result.rowcount or 0)

    async def get_plan_run(self, plan_run_id: str) -> Optional[ConversationPlanRun]:
        result = await self.db.execute(
            select(ConversationPlanRun).where(ConversationPlanRun.id == plan_run_id)
        )
        return result.scalar_one_or_none()

    async def create_plan_run(
        self,
        conv_id: str,
        destination: str,
        days: int,
        summary: dict,
    ) -> ConversationPlanRun:
        await self.lock_conversation(conv_id)
        result = await self.db.execute(
            select(func.coalesce(func.max(ConversationPlanRun.sequence), 0))
            .where(ConversationPlanRun.conversation_id == conv_id)
        )
        sequence = result.scalar_one() + 1
        run = ConversationPlanRun(
            conversation_id=conv_id,
            sequence=sequence,
            destination=destination,
            days=days,
            summary=summary,
        )
        self.db.add(run)
        await self.db.flush()
        return run

    async def list_plan_runs(self, conv_id: str) -> list[ConversationPlanRun]:
        result = await self.db.execute(
            select(ConversationPlanRun)
            .where(ConversationPlanRun.conversation_id == conv_id)
            .order_by(ConversationPlanRun.sequence.desc())
        )
        return list(result.scalars().all())

    async def add_message(self, conv_id: str, role: str, content: str,
                          message_type: str = "text",
                          metadata_json: dict | None = None,
                          client_message_id: str | None = None) -> Message:
        await self.lock_conversation(conv_id)
        if client_message_id:
            existing = (await self.db.execute(
                select(Message).where(
                    Message.conversation_id == conv_id,
                    Message.client_message_id == client_message_id,
                )
            )).scalar_one_or_none()
            if existing is not None:
                setattr(existing, "_idempotent_replay", True)
                return existing
        result = await self.db.execute(
            select(func.coalesce(func.max(Message.sequence), 0))
            .where(Message.conversation_id == conv_id)
        )
        sequence = result.scalar_one() + 1
        message = Message(
            conversation_id=conv_id,
            role=role,
            content=content,
            sequence=sequence,
            message_type=message_type,
            metadata_json=metadata_json or {},
            client_message_id=client_message_id,
        )
        self.db.add(message)
        await self.db.flush()
        return message

    async def get_messages_page(self, conv_id: str, page: int,
                                page_size: int) -> tuple[list[Message], int]:
        total = (await self.db.execute(
            select(func.count()).select_from(Message)
            .where(Message.conversation_id == conv_id)
        )).scalar_one()
        result = await self.db.execute(
            select(Message).where(Message.conversation_id == conv_id)
            .order_by(Message.sequence.desc())
            .offset((page - 1) * page_size).limit(page_size)
        )
        return list(reversed(result.scalars().all())), total

    async def get_messages_cursor(self, conv_id: str, *, before_id: str | None,
                                  after_id: str | None,
                                  limit: int) -> tuple[list[Message], bool] | None:
        cursor_id = before_id or after_id
        if cursor_id is None:
            return None
        anchor = (await self.db.execute(
            select(Message).where(
                Message.id == cursor_id,
                Message.conversation_id == conv_id,
            )
        )).scalar_one_or_none()
        if anchor is None:
            return None

        query = select(Message).where(Message.conversation_id == conv_id)
        if before_id:
            query = query.where(Message.sequence < anchor.sequence)
            query = query.order_by(Message.sequence.desc())
        else:
            query = query.where(Message.sequence > anchor.sequence)
            query = query.order_by(Message.sequence.asc())
        result = await self.db.execute(query.limit(limit + 1))
        rows = list(result.scalars().all())
        has_more = len(rows) > limit
        rows = rows[:limit]
        if not after_id:
            rows.reverse()
        return rows, has_more

    async def get_plan_runs_by_ids(self, conv_id: str,
                                   run_ids: set[str]) -> dict[str, ConversationPlanRun]:
        if not run_ids:
            return {}
        result = await self.db.execute(
            select(ConversationPlanRun).where(
                ConversationPlanRun.conversation_id == conv_id,
                ConversationPlanRun.id.in_(run_ids),
            )
        )
        return {run.id: run for run in result.scalars().all()}

    async def delete_old(self, conv_id: str, keep: int = 20):
        sub = (
            select(Message.id)
            .where(Message.conversation_id == conv_id)
            .order_by(Message.sequence.desc())
            .offset(keep)
        ).subquery()
        from sqlalchemy import delete
        await self.db.execute(delete(Message).where(Message.id.in_(select(sub.c.id))))
        await self.db.flush()
