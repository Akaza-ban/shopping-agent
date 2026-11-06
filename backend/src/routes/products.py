from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from core.tools.ecom_search import EcomSearchTool
from database.repositories import product_repository

router = APIRouter(prefix="/products", tags=["Products"])
search_tool = EcomSearchTool()

@router.get("/search")
async def search_products(
    q: str = Query(..., description="Từ khóa tìm kiếm sản phẩm"),
    platform: str = Query("all", description="Chọn nguồn: tgdd, dmx, tiki, hoặc all"),
    category: str = Query("all", description="Mã danh mục"),
    limit: int = Query(6, ge=1, le=20),
    force_refresh: bool = Query(False, description="Bắt buộc cào mới bỏ qua cache")
):
    results = await search_tool.run(
        query=q,
        category=category,
        platform=platform,
        limit=limit,
        force_refresh=force_refresh
    )
    return {
        "query": q,
        "platform": platform,
        "total": len(results),
        "data": results
    }

@router.get("/{product_id}/history")
async def get_product_price_history(product_id: str):
    """Lấy toàn bộ lịch sử biến động giá của một sản phẩm."""
    history = await product_repository.get_price_history(product_id)
    return {
        "productId": product_id,
        "total": len(history),
        "history": history
    }

@router.get("/{product_id}")
async def get_product_detail(product_id: str):
    """Lấy thông tin chi tiết của một sản phẩm từ kho CSDL."""
    prod = await product_repository.get_product_by_id(product_id)
    if not prod:
        raise HTTPException(status_code=404, detail="Sản phẩm không tồn tại trong CSDL")
    return prod

