from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from ..connection import Base

class SearchCacheModel(Base):
    __tablename__ = "search_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(String, nullable=False, index=True)
    platform = Column(String, default="all", nullable=False, index=True)
    product_ids = Column(Text, nullable=False)  # JSON-encoded list of product IDs
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)
