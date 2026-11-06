from typing import Dict, Any
from .base import BaseTool

class PriceCalculatorTool(BaseTool):
    name = "price_calculator"
    description = "Tính toán chiết khấu voucher, phí vận chuyển và quy đổi tiền tệ VND/USD"

    async def run(self, original_price: float, discount_percent: int = 0, voucher_code: str = "") -> Dict[str, Any]:
        discount_amount = original_price * (discount_percent / 100.0)
        final_price = max(0, original_price - discount_amount)
        
        return {
            "original_price": original_price,
            "discount_percent": discount_percent,
            "discount_amount": discount_amount,
            "final_price": final_price,
            "currency": "VND"
        }
