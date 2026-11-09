"""Dữ liệu vào của API góp ý / yêu cầu hỗ trợ."""

from typing import Literal

from pydantic import BaseModel, Field

FeedbackKind = Literal["feedback", "support"]
FeedbackStatus = Literal["new", "in_progress", "resolved"]


class FeedbackRequest(BaseModel):
    kind: FeedbackKind
    topic: str = Field(default="", max_length=100)
    content: str = Field(min_length=1, max_length=4000)
    contact: str = Field(default="", max_length=200)


class FeedbackUpdate(BaseModel):
    status: FeedbackStatus | None = None
    admin_note: str | None = Field(default=None, max_length=2000)
