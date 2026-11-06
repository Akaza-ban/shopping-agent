from ..state import AgentState
from ..tools.price_calculator import PriceCalculatorTool

class DealFinderAgent:
    """Agent chuyên săn voucher, tìm deal sốc và tối ưu hóa chi phí."""

    def __init__(self):
        self.calculator = PriceCalculatorTool()

    async def find_deals(self, state: AgentState) -> AgentState:
        if state.found_products:
            prod = state.found_products[0]
            if prod.discountPercent > 0:
                saved = max(0, prod.originalPrice - prod.currentPrice)
                state.final_response = (
                    f"🔥 **Ưu đãi thực tế cho sản phẩm:**\n\n"
                    f"- Sản phẩm: **{prod.name}**\n"
                    f"- Sàn phân phối: **{prod.platformName}**\n"
                    f"- Giá gốc: **{prod.originalPrice:,.0f} đ**\n"
                    f"- Giá khuyến mãi: **{prod.currentPrice:,.0f} đ** *(Giảm {prod.discountPercent}%, tiết kiệm {saved:,.0f} đ)*\n"
                    f"- Ưu đãi vận chuyển: **{prod.deliveryTag or 'Freeship'}**\n"
                    f"- Link tham khảo: [{prod.platformName}]({prod.externalUrl})"
                )
            else:
                state.final_response = (
                    f"Sản phẩm **{prod.name}** trên sàn **{prod.platformName}** hiện đang có giá bán tốt nhất là **{prod.currentPrice:,.0f} đ**.\n"
                    f"- Link tham khảo: [{prod.platformName}]({prod.externalUrl})"
                )
        else:
            state.final_response = "Vui lòng nhập tên sản phẩm hoặc dán link sản phẩm để tôi tìm kiếm ưu đãi giá thực tế cho bạn!"
        return state
