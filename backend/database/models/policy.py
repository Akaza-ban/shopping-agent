from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from ..connection import Base


class PlatformModel(Base):
    __tablename__ = "platforms"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, default="Sàn TMĐT")
    home_url = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    documents = relationship("PolicyDocumentModel", back_populates="platform", cascade="all, delete-orphan")
    terms = relationship("PolicyTermModel", back_populates="platform", cascade="all, delete-orphan")


class PolicyDocumentModel(Base):
    __tablename__ = "policy_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform_id = Column(String, ForeignKey("platforms.id", ondelete="CASCADE"), nullable=False, index=True)
    doc_type = Column(String, default="return")  # return / warranty
    title = Column(String, nullable=False)
    url = Column(String, default="")
    content = Column(Text, default="")
    content_hash = Column(String, default="")  # phát hiện trang thay đổi khi nạp lại
    fetched_at = Column(DateTime, default=datetime.utcnow)

    platform = relationship("PlatformModel", back_populates="documents")
    chunks = relationship("PolicyChunkModel", back_populates="document", cascade="all, delete-orphan")


class PolicyTermModel(Base):
    __tablename__ = "policy_terms"
    __table_args__ = (UniqueConstraint("platform_id", "category", name="uq_policy_terms_platform_category"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform_id = Column(String, ForeignKey("platforms.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("policy_documents.id", ondelete="SET NULL"), nullable=True)
    category = Column(String, default="all")
    return_window_days = Column(Integer, default=0)
    free_return = Column(Boolean, default=False)
    return_conditions_json = Column(Text, default="[]")
    return_shipping_fee = Column(String, default="")
    refund_time = Column(String, default="")
    defect_exchange = Column(String, default="")
    warranty_handling = Column(String, default="")
    exceptions_json = Column(Text, default="[]")
    last_checked = Column(DateTime, default=datetime.utcnow)

    platform = relationship("PlatformModel", back_populates="terms")


class PolicyChunkModel(Base):
    __tablename__ = "policy_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("policy_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    platform_id = Column(String, nullable=False, index=True)
    position = Column(Integer, default=0)
    text = Column(Text, nullable=False)

    document = relationship("PolicyDocumentModel", back_populates="chunks")
