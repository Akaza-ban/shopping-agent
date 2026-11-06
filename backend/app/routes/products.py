from fastapi import APIRouter, Query
from typing import List, Optional
from ...core.tools.ecom_search import EcomSearchTool

router = APIRouter(prefix="/products", tags=["Products"])
search_tool = EcomSearchTool()

@router.get("/search")
async def search_products(
    q: str = Query(..., description="Từ khóa tìm kiếm"),
    category: str = Query("all", description="Mã danh mục"),
    platform: str = Query("all", description="Mã sàn: all, tiki, lazada, shopee, tgdd, dmx"),
    limit: int = Query(6, ge=1, le=20)
):
    results = await search_tool.run(query=q, category=category, platform=platform, limit=limit)
    return {"query": q, "platform": platform, "total": len(results), "data": results}

