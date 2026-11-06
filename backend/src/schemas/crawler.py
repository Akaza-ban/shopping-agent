"""Dữ liệu vào của API quản lý crawler."""
from pydantic import BaseModel, Field


class TriggerCrawlRequest(BaseModel):
    limit_per_query: int = Field(default=3, ge=1, le=10, description="Số sản phẩm lấy tối đa cho mỗi từ khóa")
    force_refresh: bool = Field(default=True, description="Bỏ qua cache, cào dữ liệu mới nhất")
    background: bool = Field(default=True, description="Chạy ngầm không làm đơ Swagger/API")
