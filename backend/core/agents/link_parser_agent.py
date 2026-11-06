from services.catalog.platforms import display_names
from ..state import AgentState, ProductItemModel
from ..tools.url_extractor import UrlExtractorTool, unsupported_site

class LinkParserAgent:
    """Agent chịu trách nhiệm bóc tách dữ liệu từ đường dẫn link sản phẩm."""

    def __init__(self):
        self.extractor = UrlExtractorTool()

    async def parse(self, state: AgentState) -> AgentState:
        url = state.target_link or state.user_query
        site = unsupported_site(url)
        if site:
            state.found_products = []
            state.recommended_product = None
            state.final_response = (
                f"**Hệ thống chưa hỗ trợ đọc link {site}.**\n\n"
                f"Hiện tại chỉ đọc được link {display_names()}. "
                f"Hãy cho tôi biết tên sản phẩm, tôi sẽ tìm trên các sàn này."
            )
            return state

        parsed_data = await self.extractor.run(url=url)

        if parsed_data.get("priceUnavailable"):
            state.found_products = []
            state.recommended_product = None
            state.final_response = (
                f"**Chưa đọc được giá hợp lệ của sản phẩm này.**\n\n"
                f"- **Tên:** {parsed_data.get('name') or 'Không rõ'}\n"
                f"- **Sàn:** {parsed_data.get('platformName') or 'Không rõ'}\n\n"
                f"Trang có thể đang hết hàng, chỉ hiển thị giá khi chọn phiên bản, hoặc chặn truy cập tự động. "
                f"Hãy mở link để xem giá trực tiếp, hoặc hỏi tôi tìm sản phẩm này trên các sàn."
            )
            return state

        parsed_product = ProductItemModel(**parsed_data)
        state.found_products = [parsed_product]
        state.recommended_product = parsed_product
        
        state.final_response = (
            f"**Đã trích xuất thông tin sản phẩm thành công:**\n\n"
            f"- **Tên:** {parsed_product.name}\n"
            f"- **Sàn:** {parsed_product.platformName}\n"
            f"- **Giá khuyến mãi:** {parsed_product.currentPrice:,.0f} đ\n"
            f"- **Đánh giá:** {parsed_product.rating} ({parsed_product.reviewsCount})\n"
            f"- **Ghi chú AI:** {parsed_product.aiSummary}"
        )
        return state
