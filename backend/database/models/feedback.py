from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text

from ..connection import Base


class FeedbackModel(Base):
    """Góp ý / yêu cầu hỗ trợ người dùng gửi cho quản trị viên."""

    __tablename__ = "feedback_requests"

    id = Column(String, primary_key=True, index=True)
    kind = Column(String, nullable=False, index=True)  # feedback | support
    topic = Column(String, default="")
    content = Column(Text, nullable=False)
    contact = Column(String, default="")
    user_id = Column(String, index=True)
    user_email = Column(String, default="")
    user_name = Column(String, default="")
    status = Column(String, default="new", index=True)  # new | in_progress | resolved
    admin_note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow)
