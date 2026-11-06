from sqlalchemy import Column, String, Text, DateTime
from datetime import datetime
from ..connection import Base

class ChatSessionModel(Base):
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, default="Đoạn chat mới")
    summary = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
