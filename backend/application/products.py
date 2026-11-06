"""Sản phẩm: tìm trên các sàn (cache -> kho RAG -> cào trực tiếp), chi tiết và lịch sử giá trong kho."""
from typing import Any, Dict

from core.tools.ecom_search import EcomSearchTool
from database.repositories import product_repository
from shared.exceptions import NotFoundError

search_tool = EcomSearchTool()


async def search(query: str, platform: str, category: str, limit: int, force_refresh: bool) -> Dict[str, Any]:
    results = await search_tool.run(query=query, category=category, platform=platform, limit=limit,
                                    force_refresh=force_refresh)
    return {"query": query, "platform": platform, "total": len(results), "data": results}


async def price_history(product_id: str) -> Dict[str, Any]:
    history = await product_repository.get_price_history(product_id)
    return {"productId": product_id, "total": len(history), "history": history}


async def detail(product_id: str) -> Dict[str, Any]:
    product = await product_repository.get_product_by_id(product_id)
    if not product:
        raise NotFoundError("Sản phẩm không tồn tại trong CSDL")
    return product
