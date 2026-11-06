"""Câu trả lời dựng sẵn (Markdown) khi LLM offline hoặc lỗi: lượt chat không bao giờ bị sập vì LLM.

    có sản phẩm + đang đọc link   -> link_review()
    có sản phẩm                    -> recommendation()
    không có sản phẩm              -> without_products(): đã quét mà không thấy / ngoài phạm vi / chào hỏi / tư vấn chung
"""
from typing import Dict, Optional

from integrations.platforms import display_names
from services.catalog.reviews import rating_text

from ..state import ProductItemModel
from .advisor_context import format_specs_summary
from .patterns import GREETING_RE, OUT_OF_SCOPE_RE


def discount_text(p: ProductItemModel) -> str:
    savings = max(0, p.originalPrice - p.currentPrice)
    return f" *(Tiết kiệm {savings:,.0f} đ, giảm {p.discountPercent}%)*" if p.discountPercent > 0 else ""


def build_fallback(context: Dict[str, str], top: Optional[ProductItemModel], intent: Optional[str] = None) -> str:
    if top and intent == "parse_link":
        return link_review(top)
    if top:
        return recommendation(context, top)
    return without_products(context)


def link_review(p: ProductItemModel) -> str:
    """Thẩm định sản phẩm người dùng dán link."""
    savings = max(0, p.originalPrice - p.currentPrice)
    deal = (f"Sản phẩm đang được ưu đãi giảm {p.discountPercent}%, tiết kiệm {savings:,.0f} đ so với niêm yết."
            if p.discountPercent > 0 else "Giá niêm yết chuẩn chính hãng.")
    return (
        f"### Thẩm định sản phẩm từ liên kết: [{p.name}]({p.externalUrl})\n\n"
        f"- **Kênh phân phối:** **{p.platformName}** ({p.deliveryTag or 'Chính hãng'})\n"
        f"- **Mức giá hiện tại:** **{p.currentPrice:,.0f} đ**{discount_text(p)}\n"
        f"- **Độ uy tín & Đánh giá:** {rating_text(p.rating, p.reviewsCount)}\n"
        f"- **Bảo hành:** {p.warranty}\n"
        f"- **Cấu hình & Thông số cốt lõi:** {format_specs_summary(p.specs)}\n\n"
        f"### Đánh giá chuyên môn từ ShopAI\n"
        f"1. **Thẩm định giá bán:** Mức giá **{p.currentPrice:,.0f} đ** tại **{p.platformName}** là mức giá rất cạnh tranh. "
        f"{deal}\n"
        f"2. **Độ an toàn gian hàng:** Sản phẩm có nguồn gốc phân phối rõ ràng, chính sách {p.warranty}, hỗ trợ đổi trả tiêu chuẩn.\n"
        f"3. **Lời khuyên mua sắm:** Bạn có thể bấm vào liên kết trên để xem chi tiết hoặc yêu cầu tôi so sánh sản phẩm này với các đối thủ cùng phân khúc!"
    )


def recommendation(context: Dict[str, str], p: ProductItemModel) -> str:
    """Đề xuất sản phẩm xếp hạng #1 kèm bảng tóm tắt các lựa chọn."""
    relaxed_intro = (
        f"> Không tìm thấy sản phẩm khớp 100% yêu cầu của bạn. Dưới đây là các phương án gần nhất sau khi {context['relaxed_search']}.\n\n"
        if context.get("relaxed_search") else ""
    )
    return (
        f"{relaxed_intro}"
        f"### Đề xuất số 1: [{p.name}]({p.externalUrl})\n\n"
        f"- **Nơi bán:** **{p.platformName}** ({p.deliveryTag or 'Chính hãng'})\n"
        f"- **Mức giá ưu đãi:** **{p.currentPrice:,.0f} đ**{discount_text(p)}\n"
        f"- **Đánh giá người dùng:** {rating_text(p.rating, p.reviewsCount)}\n"
        f"- **Cấu hình nổi bật:** {format_specs_summary(p.specs)}\n\n"
        f"### So sánh nhanh Top lựa chọn\n"
        f"{context['products_context']}\n\n"
        f"### Lời khuyên mua sắm từ ShopAI\n"
        f"Mẫu **{p.name}** tại **{p.platformName}** hiện là lựa chọn cân bằng tốt nhất giữa giá cả và cấu hình. "
        f"Bạn có thể nhấn vào liên kết sản phẩm để xem chi tiết hoặc yêu cầu tôi so sánh chuyên sâu hơn."
    )


def without_products(context: Dict[str, str]) -> str:
    """Không có sản phẩm: đã quét mà không thấy / ngoài phạm vi / chào hỏi / tư vấn chung."""
    query = context["user_query"]
    q_lower = query.lower().strip()
    if context.get("searched"):
        return (
            f"### Chưa tìm thấy sản phẩm phù hợp\n\n"
            f"Tôi đã quét {display_names()} và kho dữ liệu cho **\"{query}\"** "
            f"nhưng chưa có sản phẩm nào đáp ứng, kể cả sau khi thử nới lỏng tiêu chí.\n\n"
            f"Bạn có thể thử: nới ngân sách, bớt một yêu cầu cấu hình, hoặc cho tôi biết hãng/mẫu cụ thể bạn quan tâm."
        )
    if OUT_OF_SCOPE_RE.search(q_lower):
        return (
            f"### ShopAI Copilot - Trợ lý Mua sắm Thông minh\n\n"
            f"Rất tiếc, câu hỏi của bạn nằm ngoài phạm vi tư vấn mua sắm của tôi.\n\n"
            f"Là trợ lý AI chuyên trách mua sắm công nghệ và tiêu dùng tại Việt Nam, tôi chỉ có thể hỗ trợ bạn:\n"
            f"- **Tư vấn chọn mua:** Laptop, điện thoại, máy tính bảng, đồ gia dụng, âm thanh...\n"
            f"- **So sánh trực quan:** Cấu hình, ưu nhược điểm và so sánh giá giữa {display_names()}.\n"
            f"- **Săn deal & Khuyến mãi:** Tìm kiếm mức giá tốt nhất tại các gian hàng chính hãng uy tín.\n\n"
            f"**Bạn có muốn tôi hỗ trợ tìm kiếm hoặc tư vấn về sản phẩm mua sắm nào không?**"
        )
    if GREETING_RE.search(q_lower):
        return (
            f"### Chào bạn! Tôi là ShopAI Copilot\n\n"
            f"Tôi là trợ lý AI chuyên gia tư vấn mua sắm công nghệ và tiêu dùng tại Việt Nam.\n\n"
            f"**Tôi có thể hỗ trợ bạn:**\n"
            f"- **Tư vấn chọn mua:** Laptop, điện thoại, máy tính bảng, đồ gia dụng theo ngân sách.\n"
            f"- **So sánh trực quan:** Cấu hình, giá bán giữa {display_names()}.\n"
            f"- **Săn ưu đãi:** Tìm kiếm khuyến mãi và gian hàng chính hãng uy tín.\n\n"
            f"**Hôm nay bạn đang quan tâm đến sản phẩm nào?** Hãy chia sẻ với tôi nhé!"
        )
    return (
        f"### Tư Vấn Mua Sắm Từ ShopAI Copilot\n\n"
        f"Về câu hỏi **\"{query}\"**:\n\n"
        f"1. **Định hướng lựa chọn:** Dựa trên nhu cầu thực tế, bạn nên cân nhắc giữa tỷ lệ hiệu năng/giá thành (đời máy trước thường tiết kiệm hơn đáng kể) và thời gian hỗ trợ cập nhật lâu dài (đời máy mới hơn).\n"
        f"2. **Đặc thù các sàn TMĐT & chuỗi bán lẻ:**\n"
        f"   - **Tiki Trading:** Giá thường ưu đãi nhất nhờ nhiều mã giảm giá và flash sale.\n"
        f"   - **Thế Giới Di Động / Điện Máy Xanh:** Lợi thế mạng lưới siêu thị rộng khắp, trải nghiệm máy thực tế và hỗ trợ kỹ thuật tại chỗ.\n\n"
        f"**Bạn có muốn tôi quét trực tiếp giá bán và khuyến mãi mới nhất hiện có tại {display_names()} không?** Hãy cho tôi biết mẫu máy bạn quan tâm nhất nhé!"
    )
