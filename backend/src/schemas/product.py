"""Sản phẩm trong hợp đồng API (giao diện gửi lên / nhận về).

Tách khỏi ProductItemModel của agent (core/state.py): sửa state nội bộ của agent không làm đổi API.
Trường dùng camelCase vì giao diện đang dùng tên này.
"""
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ProductOut(BaseModel):
    id: str
    name: str
    category: str = "all"
    categoryName: str = "Tất cả"
    platform: str
    platformName: str
    platformBadgeColor: str = "#ee4d2d"
    platformBadgeBg: str = "rgba(238, 77, 45, 0.15)"
    aiMatchScore: int = 90
    originalPrice: float
    currentPrice: float
    discountPercent: int = 0
    rating: float = 4.8
    reviewsCount: str = "100+ đánh giá"
    sku: str = ""
    image: str = ""
    specs: Optional[Union[Dict[str, Any], str]] = ""
    aiSummary: str = ""
    warranty: str = "Chính hãng 12 tháng"
    deliveryTag: Optional[str] = "Freeship"
    selected: bool = False
    externalUrl: str = ""
    sourceCategoryPath: Optional[str] = None
    sourceCategoryName: Optional[str] = None
    updatedAt: Optional[str] = None
    returnPolicy: Optional[str] = None
    detailFetched: bool = False
    matchReasons: List[str] = Field(default_factory=list)
    attributeMatch: Dict[str, str] = Field(default_factory=dict)  # thuộc tính -> verified | mismatch | unknown
