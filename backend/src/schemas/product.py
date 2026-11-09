"""Sản phẩm trong hợp đồng API (giao diện gửi lên / nhận về).

Tách khỏi ProductItemModel của agent (core/state.py): sửa state nội bộ của agent không làm đổi API.
Trường dùng camelCase vì giao diện đang dùng tên này.
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator

from shared.unverified import PLACEHOLDER_DELIVERY, PLACEHOLDER_REVIEWS, PLACEHOLDER_WARRANTIES, known


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
    rating: float = 0.0  # 0 = chưa có đánh giá
    reviewsCount: str = ""
    sku: str = ""
    image: str = ""
    specs: dict[str, Any] | str | None = ""
    aiSummary: str = ""
    warranty: str | None = None  # None = chưa rõ
    deliveryTag: str | None = None
    selected: bool = False
    externalUrl: str = ""
    sourceCategoryPath: str | None = None
    sourceCategoryName: str | None = None
    updatedAt: str | None = None
    returnPolicy: str | None = None
    detailFetched: bool = False
    matchReasons: list[str] = Field(default_factory=list)
    attributeMatch: dict[str, str] = Field(default_factory=dict)  # thuộc tính -> verified | mismatch | unknown

    # Sản phẩm lưu từ phiên bản cũ có thể còn giá trị điền sẵn (shared/unverified.py)
    @field_validator("warranty", mode="before")
    @classmethod
    def _real_warranty(cls, v):
        return known(v, PLACEHOLDER_WARRANTIES)

    @field_validator("deliveryTag", mode="before")
    @classmethod
    def _real_delivery(cls, v):
        return known(v, PLACEHOLDER_DELIVERY)

    @field_validator("reviewsCount", mode="before")
    @classmethod
    def _real_reviews(cls, v):
        return known(v, PLACEHOLDER_REVIEWS) or ""
