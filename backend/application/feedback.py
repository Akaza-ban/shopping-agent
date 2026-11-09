"""Góp ý / yêu cầu hỗ trợ: người dùng gửi, quản trị viên xem và xử lý."""

from datetime import datetime, timedelta
from typing import Any

from database.models import UserModel
from database.repositories import feedback_repository
from shared.exceptions import NotFoundError, RateLimitedError, ValidationFailedError

# Chống gửi dồn: tối đa 10 yêu cầu mỗi giờ cho một tài khoản
MAX_PER_HOUR = 10
MY_FEEDBACK_LIMIT = 50


async def submit(user: UserModel, kind: str, topic: str, content: str, contact: str) -> dict[str, Any]:
    content = content.strip()
    if not content:
        raise ValidationFailedError("Nội dung không được để trống.")
    if await feedback_repository.recent_count(user.id, datetime.utcnow() - timedelta(hours=1)) >= MAX_PER_HOUR:
        raise RateLimitedError("Bạn đã gửi khá nhiều yêu cầu trong một giờ qua, vui lòng thử lại sau.")
    return await feedback_repository.create(
        {
            "kind": kind,
            "topic": topic.strip(),
            "content": content,
            "contact": contact.strip(),
            "user_id": user.id,
            "user_email": user.email,
            "user_name": user.display_name,
        }
    )


async def list_mine(user: UserModel) -> list[dict[str, Any]]:
    """Các yêu cầu chính người dùng đã gửi (kèm trạng thái xử lý)."""
    return await feedback_repository.list(user_id=user.id, limit=MY_FEEDBACK_LIMIT)


async def inbox(status: str | None, kind: str | None) -> dict[str, Any]:
    """Quản trị viên: danh sách (mới nhất trước) và số lượng theo trạng thái."""
    return {
        "items": await feedback_repository.list(status=status, kind=kind),
        "counts": await feedback_repository.counts(),
    }


async def update(feedback_id: str, status: str | None, admin_note: str | None) -> dict[str, Any]:
    """Quản trị viên: đổi trạng thái xử lý / ghi chú nội bộ."""
    updated = await feedback_repository.update(
        feedback_id, status=status, admin_note=admin_note.strip() if admin_note is not None else None
    )
    if updated is None:
        raise NotFoundError("Không tìm thấy yêu cầu.")
    return updated
