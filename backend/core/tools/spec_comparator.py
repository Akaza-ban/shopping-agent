from typing import List, Dict, Any
from .base import BaseTool

class SpecComparatorTool(BaseTool):
    name = "spec_comparator"
    description = "So sánh thông số kỹ thuật và tính toán độ chênh lệch giá giữa các sản phẩm"

    async def run(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not products:
            return {"status": "empty", "message": "Không có sản phẩm để so sánh"}
        
        # Tìm sản phẩm có giá thấp nhất
        sorted_by_price = sorted(products, key=lambda x: x.get("currentPrice", float("inf")))
        cheapest = sorted_by_price[0]
        
        return {
            "total_compared": len(products),
            "best_deal": cheapest,
            "price_diff": sorted_by_price[-1].get("currentPrice", 0) - cheapest.get("currentPrice", 0),
            "recommendation": f"Sản phẩm {cheapest.get('name')} trên {cheapest.get('platformName')} đang có mức giá cạnh tranh nhất."
        }
