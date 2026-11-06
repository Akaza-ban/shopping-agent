from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String, Text

from ..connection import Base


class CategoryMappingModel(Base):
    """Danh mục của một sàn -> ngành hàng chuẩn của hệ thống; do LLM quy đổi lần đầu, sửa tay được (decided_by)."""
    __tablename__ = "category_mappings"

    source_key = Column(String, primary_key=True)
    platform = Column(String, nullable=False, index=True)
    label = Column(String, default="")  # mô tả danh mục gửi cho LLM
    samples_json = Column(Text, default="[]")
    category = Column(String, nullable=False)
    is_accessory = Column(Boolean, default=False)
    product_noun = Column(String, default="")
    decided_by = Column(String, default="llm")  # llm / manual (sửa tay thì không bị ghi đè)
    updated_at = Column(DateTime, default=datetime.utcnow)
