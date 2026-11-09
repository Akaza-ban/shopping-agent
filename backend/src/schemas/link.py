"""Dữ liệu vào của API đọc link sản phẩm."""

from pydantic import BaseModel, Field


class ParseLinkRequest(BaseModel):
    url: str = Field(max_length=2000)
