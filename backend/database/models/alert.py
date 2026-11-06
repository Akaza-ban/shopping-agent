from sqlalchemy import Column, String, Float, DateTime
from datetime import datetime
from ..connection import Base

class AlertModel(Base):
    __tablename__ = "price_alerts"

    id = Column(String, primary_key=True, index=True)
    product_name = Column(String, nullable=False)
    target_price = Column(Float, nullable=False)
    platform = Column(String, default="all")
    user_email = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
