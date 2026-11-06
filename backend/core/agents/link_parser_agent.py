from ..state import AgentState, ProductItemModel
from ..tools.url_extractor import UrlExtractorTool

class LinkParserAgent:
    """Agent chịu trách nhiệm bóc tách dữ liệu từ đường dẫn link sản phẩm."""

    def __init__(self):
        self.extractor = UrlExtractorTool()

    async def parse(self, state: AgentState) -> AgentState:
        url = state.target_link or state.user_query
        parsed_data = await self.extractor.run(url=url)
        
        parsed_product = ProductItemModel(**parsed_data)
        state.found_products = [parsed_product]
        state.recommended_product = parsed_product
        
        state.final_response = (
            f"✅ **Đã trích xuất thông tin sản phẩm thành công:**\n\n"
            f"- **Tên:** {parsed_product.name}\n"
            f"- **Sàn:** {parsed_product.platformName}\n"
            f"- **Giá khuyến mãi:** {parsed_product.currentPrice:,.0f} đ\n"
            f"- **Đánh giá:** ⭐ {parsed_product.rating} ({parsed_product.reviewsCount})\n"
            f"- **Ghi chú AI:** {parsed_product.aiSummary}"
        )
        return state
