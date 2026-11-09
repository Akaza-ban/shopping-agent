import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select

from database.repositories.serialization import iso

from ..connection import async_session
from ..errors import raises_database_error
from ..models import FeedbackModel

STATUSES = ("new", "in_progress", "resolved")


def feedback_to_dict(f: FeedbackModel) -> dict[str, Any]:
    return {
        "id": f.id,
        "kind": f.kind,
        "topic": f.topic or "",
        "content": f.content,
        "contact": f.contact or "",
        "userId": f.user_id,
        "userEmail": f.user_email or "",
        "userName": f.user_name or "",
        "status": f.status or "new",
        "adminNote": f.admin_note or "",
        "createdAt": iso(f.created_at),
        "updatedAt": iso(f.updated_at),
    }


@raises_database_error
class FeedbackRepository:
    def __init__(self, session_factory=async_session):
        self.session_factory = session_factory

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        now = datetime.utcnow()
        async with self.session_factory() as session:
            item = FeedbackModel(id=f"fb-{uuid.uuid4().hex[:12]}", status="new", created_at=now, updated_at=now, **data)
            session.add(item)
            await session.commit()
            return feedback_to_dict(item)

    async def list(
        self, status: str | None = None, kind: str | None = None, user_id: str | None = None, limit: int = 200
    ) -> list[dict[str, Any]]:
        async with self.session_factory() as session:
            stmt = select(FeedbackModel).order_by(FeedbackModel.created_at.desc()).limit(limit)
            if status:
                stmt = stmt.where(FeedbackModel.status == status)
            if kind:
                stmt = stmt.where(FeedbackModel.kind == kind)
            if user_id:
                stmt = stmt.where(FeedbackModel.user_id == user_id)
            return [feedback_to_dict(f) for f in (await session.execute(stmt)).scalars().all()]

    async def counts(self) -> dict[str, int]:
        """Số yêu cầu theo trạng thái (đủ 3 trạng thái, kể cả khi bằng 0)."""
        async with self.session_factory() as session:
            rows = await session.execute(select(FeedbackModel.status, func.count()).group_by(FeedbackModel.status))
            found = {status: n for status, n in rows.all()}
        return {s: found.get(s, 0) for s in STATUSES}

    async def recent_count(self, user_id: str, since: datetime) -> int:
        async with self.session_factory() as session:
            stmt = (
                select(func.count())
                .select_from(FeedbackModel)
                .where(FeedbackModel.user_id == user_id, FeedbackModel.created_at >= since)
            )
            return (await session.execute(stmt)).scalar() or 0

    async def update(
        self, feedback_id: str, status: str | None = None, admin_note: str | None = None
    ) -> dict[str, Any] | None:
        async with self.session_factory() as session:
            item = await session.get(FeedbackModel, feedback_id)
            if item is None:
                return None
            if status is not None:
                item.status = status
            if admin_note is not None:
                item.admin_note = admin_note
            item.updated_at = datetime.utcnow()
            await session.commit()
            return feedback_to_dict(item)


feedback_repository = FeedbackRepository()
