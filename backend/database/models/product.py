from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import relationship

from ..connection import Base


class ProductModel(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    category = Column(String, default="other", index=True)
    source_category_path = Column(String, nullable=True)
    category_name = Column(String, default="Sản phẩm")
    platform = Column(String, nullable=False, index=True)
    platform_name = Column(String, nullable=False)
    original_price = Column(Float, default=0.0)
    current_price = Column(Float, default=0.0, index=True)
    discount_percent = Column(Integer, default=0)
    rating = Column(Float, default=5.0)
    reviews_count = Column(String, default="Chính hãng")
    image = Column(String, default="")
    specs = Column(Text, default="")
    ai_summary = Column(Text, default="")
    warranty = Column(String, default="")
    delivery_tag = Column(String, default="")
    external_url = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    price_history = relationship(
        "PriceHistoryModel",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="desc(PriceHistoryModel.recorded_at)",
    )
