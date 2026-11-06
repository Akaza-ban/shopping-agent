from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from datetime import datetime
from ..connection import Base

class AlertModel(Base):
    """Theo dõi giá: báo khi giá bán của một sản phẩm cụ thể giảm xuống mức mong muốn."""
    __tablename__ = "price_alerts"

    id = Column(String, primary_key=True, index=True)
    product_name = Column(String, nullable=False)
    target_price = Column(Float, nullable=False)
    platform = Column(String, default="all")
    user_email = Column(String, nullable=False, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    user_id = Column(String, index=True)
    product_id = Column(String, index=True)
    product_url = Column(String, default="")
    image = Column(String, default="")
    platform_name = Column(String, default="")
    initial_price = Column(Float)
    last_price = Column(Float)
    lowest_price = Column(Float)
    status = Column(String, default="watching", index=True)
    last_checked_at = Column(DateTime)
    triggered_at = Column(DateTime)
    last_note = Column(Text, default="")
    pending_price = Column(Float)
    pending_at = Column(DateTime)
    in_stock = Column(Boolean)


class PriceCheckModel(Base):
    """Nhật ký từng lần kiểm tra giá (kết quả guardrails), thay cho danh sách trong RAM."""
    __tablename__ = "price_checks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String, index=True, nullable=False)
    user_id = Column(String, index=True)
    product_name = Column(String, default="")
    price = Column(Float)
    in_stock = Column(Boolean)
    outcome = Column(String, nullable=False)
    note = Column(Text, default="")
    latency_ms = Column(Float)
    checked_at = Column(DateTime, default=datetime.utcnow, index=True)
