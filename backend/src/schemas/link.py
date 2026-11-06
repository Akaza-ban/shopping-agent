"""Dữ liệu vào của API đọc link sản phẩm."""
from pydantic import BaseModel


class ParseLinkRequest(BaseModel):
    url: str
