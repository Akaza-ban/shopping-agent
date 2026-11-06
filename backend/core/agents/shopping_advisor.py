from ..state import AgentState, MessageItem
from ..prompts.advisor_prompts import ADVISOR_SYSTEM_PROMPT
from src.config import settings, get_chat_model
import time

class ShoppingAdvisorAgent:
    """Agent tư vấn giải đáp, đề xuất sản phẩm và tổng hợp câu trả lời."""

    async def generate_response(self, state: AgentState) -> AgentState:
        # Nếu có sản phẩm tìm thấy, tạo câu trả lời tổng hợp kèm đề xuất
        if state.found_products:
            top_prod = state.found_products[0]
            state.recommended_product = top_prod
            
            response_text = (
                f"### 🤖 Tư Vấn ShopAI Copilot\n\n"
                f"Dựa trên yêu cầu **\"{state.user_query}\"**, tôi đã phân tích và tìm thấy các lựa chọn tối ưu nhất:\n\n"
                f"- **Sản phẩm đề xuất:** {top_prod.name}\n"
                f"- **Sàn thương mại:** {top_prod.platformName}\n"
                f"- **Mức giá ưu đãi:** {top_prod.currentPrice:,.0f} đ *(Giảm {top_prod.discountPercent}%)*\n"
                f"- **Đánh giá:** ⭐ {top_prod.rating} ({top_prod.reviewsCount})\n"
                f"- **Điểm phân tích AI:** {top_prod.aiMatchScore}/100\n\n"
                f"> **Nhận xét chuyên gia:** {top_prod.aiSummary}\n\n"
                f"Bạn có muốn tôi so sánh chi tiết mẫu này với sàn khác hoặc kiểm tra thêm mã giảm giá không?"
            )
        else:
            response_text = (
                f"Chào bạn! Tôi là ShopAI Copilot. Về câu hỏi **\"{state.user_query}\"**:\n\n"
                f"Để tôi có thể tư vấn chính xác nhất, bạn có thể chia sẻ thêm về:\n"
                f"1. **Mức ngân sách tối đa** bạn dự định chi trả?\n"
                f"2. **Nhu cầu sử dụng chính** (Học tập, làm việc văn phòng, chơi game hay đồ họa)?\n"
                f"3. Sàn TMĐT bạn ưu tiên mua sắm (Shopee, Tiki hay Lazada)?"
            )

        state.final_response = response_text
        ai_message = MessageItem(
            id=f"msg-ai-{int(time.time() * 1000)}",
            sender="ai",
            text=response_text,
            timestamp="Vừa xong",
            precision="98.5%"
        )
        state.messages.append(ai_message)
        return state
