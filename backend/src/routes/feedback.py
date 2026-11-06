"""API góp ý / yêu cầu hỗ trợ. Logic nằm ở application/feedback.py."""
from typing import Optional

from fastapi import APIRouter, Depends

import application.feedback as feedback
from database.models import UserModel
from src.dependencies.auth import require_admin, require_user
from src.schemas.feedback import FeedbackKind, FeedbackRequest, FeedbackStatus, FeedbackUpdate

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post("", status_code=201)
async def submit_feedback(req: FeedbackRequest, user: UserModel = Depends(require_user)):
    """Người dùng gửi góp ý / yêu cầu hỗ trợ cho quản trị viên."""
    return await feedback.submit(user, req.kind, req.topic, req.content, req.contact)


@router.get("/mine")
async def my_feedback(user: UserModel = Depends(require_user)):
    return await feedback.list_mine(user)


@router.get("")
async def list_feedback(status: Optional[FeedbackStatus] = None, kind: Optional[FeedbackKind] = None,
                        user: UserModel = Depends(require_admin)):
    return await feedback.inbox(status, kind)


@router.patch("/{feedback_id}")
async def update_feedback(feedback_id: str, req: FeedbackUpdate, user: UserModel = Depends(require_admin)):
    return await feedback.update(feedback_id, req.status, req.admin_note)
