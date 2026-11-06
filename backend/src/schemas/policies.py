"""Dữ liệu vào của API tra cứu chính sách."""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class LookupRequest(BaseModel):
    query: str = Field("", max_length=300)
    platform_ids: List[str] = Field(default_factory=list)
    category: str = "all"
    language: Literal["vi", "en"] = "vi"
    product_platform_ids: List[str] = Field(default_factory=list)
    scenario: Optional[Literal["defect", "change_mind", "wrong_item", "warranty"]] = None
