from sqlalchemy import Column, String, Text, DateTime
from datetime import datetime
from ..connection import Base

class ChatSessionModel(Base):
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, default="Đoạn chat mới")
    summary = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(String, index=True)

class ChatMessageModel(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=False)
    sender = Column(String, nullable=False)  
    text = Column(Text, nullable=False)
    products_json = Column(Text, default="[]")  
    criteria_json = Column(Text, default="{}")  
    timestamp = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

class ConversationStateModel(Base):
    __tablename__ = "conversation_states"

    session_id = Column(String, primary_key=True, index=True)
    state_json = Column(Text, default="{}")
    updated_at = Column(DateTime, default=datetime.utcnow)
