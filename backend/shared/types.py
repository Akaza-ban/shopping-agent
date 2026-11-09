"""Kiểu dữ liệu dùng chung.

RawProduct: sản phẩm dạng dict đi qua tầng cào / tìm kiếm / xếp hạng (trước khi thành ProductItemModel của agent).
Mọi trường đều không bắt buộc vì mỗi nguồn (sàn, cache, kho RAG, link) điền một phần; tên trường camelCase
giống giao diện.
"""

from typing import Any, TypedDict


class RawProduct(TypedDict, total=False):
    id: str
    name: str
    category: str  # mã ngành hàng chuẩn (shared/categories.py)
    categoryName: str
    sourceCategoryPath: str  # danh mục theo sàn, dùng để quy đổi ngành hàng
    sourceCategoryName: str
    platform: str  # mã sàn: tgdd, dmx, tiki, fpt-shop, cellphones
    platformName: str
    platformBadgeColor: str
    platformBadgeBg: str
    currentPrice: float
    originalPrice: float
    discountPercent: int
    rating: float  # 0 = chưa có đánh giá
    reviewsCount: str
    sku: str
    image: str
    specs: dict[str, Any] | str
    aiSummary: str
    aiMatchScore: int  # điểm phù hợp 0-100 do bộ xếp hạng tính
    warranty: str
    returnPolicy: str
    deliveryTag: str
    externalUrl: str
    updatedAt: str
    detailFetched: bool  # đã đọc trang chi tiết chưa
    matchReasons: list[str]  # lý do cộng / trừ điểm của bộ xếp hạng
    attributeMatch: dict[str, str]  # thông số bắt buộc -> verified | mismatch | unknown
    priceUnavailable: bool  # đọc link mà không lấy được giá hợp lệ
