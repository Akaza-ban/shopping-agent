"""API sản phẩm. Logic nằm ở application/products.py."""

from fastapi import APIRouter, Depends, Query

import application.products as products
from database.models import UserModel
from shared.exceptions import PermissionDeniedError
from src.dependencies.auth import require_user
from src.dependencies.rate_limit import rate_limit

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/search", dependencies=[Depends(rate_limit("product_search"))])
async def search_products(
    q: str = Query(..., min_length=1, max_length=200, description="Từ khóa tìm kiếm sản phẩm"),
    platform: str = Query("all", description="Chọn nguồn: tgdd, dmx, tiki, hoặc all"),
    category: str = Query("all", description="Mã danh mục"),
    limit: int = Query(6, ge=1, le=20),
    force_refresh: bool = Query(False, description="Bắt buộc cào mới bỏ qua cache (chỉ quản trị viên)"),
    user: UserModel = Depends(require_user),
):
    if force_refresh and user.role != "admin":  # cào liên tục dễ bị sàn chặn IP của server
        raise PermissionDeniedError("Chỉ quản trị viên được bắt buộc cào mới.")
    return await products.search(q, platform, category, limit, force_refresh)


@router.get("/{product_id}/history")
async def get_product_price_history(product_id: str):
    """Toàn bộ lịch sử biến động giá của một sản phẩm."""
    return await products.price_history(product_id)


@router.get("/{product_id}")
async def get_product_detail(product_id: str):
    """Thông tin chi tiết của một sản phẩm trong kho."""
    return await products.detail(product_id)
