from services.catalog.platforms import display_names
import re
import time
import asyncio
import logging
from typing import List, Dict, Any, Optional

from langchain_core.messages import SystemMessage, HumanMessage
from ..state import AgentState, MessageItem, ProductItemModel, UniversalSearchCriteria
from ..prompts.advisor_prompts import ADVISOR_SYSTEM_PROMPT, ADVISOR_USER_PROMPT_TEMPLATE
from .patterns import GREETING_RE, OUT_OF_SCOPE_RE
from src.config import settings, get_chat_model

logger = logging.getLogger("shopping_advisor")


def language_instruction(language: str) -> str:
    """Chỉ dẫn ngôn ngữ trả lời thêm vào system prompt (mặc định tiếng Việt)."""
    if language == "en":
        return (
            "\n\nLANGUAGE: Write the entire answer in English. Keep product names, prices (VND), "
            "platform names and technical specs exactly as provided; do not translate product names."
        )
    return ""


def _discount_text(p) -> str:
    savings = max(0, p.originalPrice - p.currentPrice)
    return f" *(Tiết kiệm {savings:,.0f} đ, giảm {p.discountPercent}%)*" if p.discountPercent > 0 else ""


async def _stream_words(text: str, size: int = 4):
    """Phát câu trả lời dựng sẵn theo từng cụm vài từ để giao diện vẫn có hiệu ứng gõ chữ."""
    words = text.split(" ")
    for i in range(0, len(words), size):
        yield " ".join(words[i:i + size]) + " "
        await asyncio.sleep(0.015)

class ShoppingAdvisorAgent:
    """Agent chuyên gia tư vấn mua sắm ShopAI Copilot."""

    def _format_specs_summary(self, specs: Any) -> str:
        """Chuẩn hóa thông số kỹ thuật (Specs) thành một chuỗi ngắn gọn trên 1 dòng."""
        if not specs:
            return "Chính hãng, đầy đủ phụ kiện"

        if isinstance(specs, dict):
            from core.tools.spec_comparator import PREFERRED_SPEC_ROWS
            ordered_keys = [k for k in PREFERRED_SPEC_ROWS if specs.get(k)] + [k for k in specs if k not in PREFERRED_SPEC_ROWS]
            compact_items = []
            for k in ordered_keys:
                v = specs.get(k)
                if k and v:
                    compact_items.append(f"{k}: {str(v)[:70]}")
                if len(compact_items) >= 7:
                    break
            return " | ".join(compact_items) if compact_items else "Chính hãng, đầy đủ phụ kiện"

        # Nếu specs là chuỗi (string)
        specs_str = str(specs).strip()
        if len(specs_str) > 120:
            specs_str = specs_str[:120] + "..."
        return specs_str or "Chính hãng, đầy đủ phụ kiện"

    def _format_single_product(self, idx: int, p: ProductItemModel) -> str:
        """Định dạng 1 sản phẩm thành bản tóm tắt 3 dòng súc tích và giàu thông tin."""
        savings = max(0, p.originalPrice - p.currentPrice)
        discount_str = f" (Giảm {p.discountPercent}%, tiết kiệm {savings:,.0f} đ)" if p.discountPercent > 0 else ""
        specs_line = self._format_specs_summary(p.specs)
        rating_str = f"{p.rating}/5.0 ({p.reviewsCount})" if p.rating and p.rating > 0 else f"Chưa có đánh giá ({p.reviewsCount})"

        reasons = "; ".join(p.matchReasons) if p.matchReasons else "không có"
        return (
            f"[Lựa chọn #{idx}] Điểm phù hợp: {p.aiMatchScore}/100 (lý do: {reasons})\n"
            f"- Tên & Sàn: {p.name} (Bán tại: {p.platformName})\n"
            f"- Giá ưu đãi: {p.currentPrice:,.0f} đ{discount_str} | Đánh giá: {rating_str}\n"
            f"- Cấu hình ({'đã đọc trang chi tiết' if p.detailFetched else 'chỉ từ trang danh sách'}): {specs_line}\n"
            f"- Bảo hành: {p.warranty or 'Chưa rõ'} | Đổi trả: {p.returnPolicy or 'Theo chính sách của sàn'} | Vận chuyển: {p.deliveryTag or 'Giao tiêu chuẩn'}\n"
            f"- Link: {p.externalUrl or 'không có'}"
        )

    def _format_products_context(
        self,
        products: List[ProductItemModel],
        max_items: int = 3,
        searched: bool = False
    ) -> str:
        """Chuẩn hóa danh sách sản phẩm thành khối ngữ cảnh:"""
        if not products:
            if searched:
                return (
                    f"KHÔNG TÌM THẤY SẢN PHẨM: hệ thống đã quét các sàn ({display_names()}) "
                    "và kho dữ liệu nhưng không có sản phẩm nào phù hợp, kể cả sau khi đã thử nới lỏng tiêu chí. "
                    "Không có dữ liệu giá nào để trích dẫn."
                )
            return "Lượt này không quét sàn (câu hỏi tư vấn định hướng). Chỉ tư vấn kiến thức chuyên môn, không nêu giá cụ thể."

        top_candidates = products[:max_items]
        formatted_items = [
            self._format_single_product(idx=i, p=prod)
            for i, prod in enumerate(top_candidates, 1)
        ]
        return "\n\n".join(formatted_items)

    def _format_criteria_context(self, criteria: Optional[UniversalSearchCriteria]) -> str:
        """Chuẩn hóa các ràng buộc/tiêu chí của người dùng nếu có."""
        if not criteria:
            return ""

        parts = []
        if criteria.category and criteria.category != "all":
            parts.append(f"Ngành hàng: {criteria.category_name or criteria.category}")
        if criteria.brands:
            parts.append(f"Hãng ưu tiên: {', '.join(criteria.brands)}")
        if criteria.max_price:
            parts.append(f"Ngân sách tối đa: {criteria.max_price:,.0f} đ")
        if criteria.min_price:
            parts.append(f"Ngân sách tối thiểu: {criteria.min_price:,.0f} đ")
        if criteria.usage_purpose:
            parts.append(f"Mục đích: {criteria.usage_purpose}")

        return f"Yêu cầu bổ sung của khách hàng: {'; '.join(parts)}" if parts else ""

    def build_standardized_context(self, state: AgentState) -> Dict[str, str]:
        """Tổng hợp và Chuẩn hóa toàn bộ Ngữ cảnh Đầu vào (Input Context)."""
        from memory.session_manager import session_memory

        searched = state.intent in ("search_products", "compare_products", "find_deal")
        effective_products = state.found_products
        if not effective_products and not searched and state.session_id:
            raw_last = session_memory.get_last_products(state.session_id)
            if raw_last:
                effective_products = [ProductItemModel(**p) for p in raw_last]

        products_context = self._format_products_context(effective_products, max_items=3, searched=searched)
        criteria_summary = self._format_criteria_context(state.criteria)

        chat_history = session_memory.format_chat_history_for_prompt(state.session_id, max_turns=3) if state.session_id else ""
        chat_history_context = f"[Lịch sử trao đổi trước đó]:\n{chat_history}" if chat_history else ""

        notes_parts = []
        if state.relaxed_search:
            notes_parts.append(f"Tiêu chí đã nới lỏng: {state.relaxed_search} (không có sản phẩm khớp 100% yêu cầu gốc).")
        if state.comparison_summary:
            notes_parts.append(f"Kết quả công cụ so sánh: {state.comparison_summary}")
        if state.comparison_markdown:
            notes_parts.append(
                "Bảng so sánh do công cụ tạo (ô in đậm là tốt nhất của hàng; giao diện đã hiển thị bảng này, "
                "chỉ cần tóm tắt điểm khác biệt chính):\n" + state.comparison_markdown
            )
        if state.search_notes:
            notes_parts.append("Ghi chú độ tin cậy:\n" + "\n".join(f"- {n}" for n in state.search_notes))
        search_notes_context = "\n".join(notes_parts)

        return {
            "user_query": state.user_query,
            "criteria_summary": criteria_summary,
            "chat_history_context": chat_history_context,
            "products_context": products_context,
            "search_notes_context": search_notes_context,
            "searched": "1" if searched else "",
            "relaxed_search": state.relaxed_search or "",
            "total_found": str(len(effective_products))
        }

    def _build_deterministic_fallback(self, context: Dict[str, str], top_prod: Optional[ProductItemModel], intent: Optional[str] = None) -> str:
        """Câu trả lời dựng sẵn (Markdown) khi LLM offline hoặc lỗi, không bao giờ làm sập lượt chat."""
        if top_prod and intent == "parse_link":
            return self._fallback_link_review(top_prod)
        if top_prod:
            return self._fallback_recommendation(context, top_prod)
        return self._fallback_without_products(context)

    def _fallback_link_review(self, p: ProductItemModel) -> str:
        """Thẩm định sản phẩm người dùng dán link."""
        savings = max(0, p.originalPrice - p.currentPrice)
        deal = (f"Sản phẩm đang được ưu đãi giảm {p.discountPercent}%, tiết kiệm {savings:,.0f} đ so với niêm yết."
                if p.discountPercent > 0 else "Giá niêm yết chuẩn chính hãng.")
        return (
            f"### Thẩm định sản phẩm từ liên kết: [{p.name}]({p.externalUrl})\n\n"
            f"- **Kênh phân phối:** **{p.platformName}** ({p.deliveryTag or 'Chính hãng'})\n"
            f"- **Mức giá hiện tại:** **{p.currentPrice:,.0f} đ**{_discount_text(p)}\n"
            f"- **Độ uy tín & Đánh giá:** {p.rating} / 5.0 ({p.reviewsCount})\n"
            f"- **Bảo hành:** {p.warranty}\n"
            f"- **Cấu hình & Thông số cốt lõi:** {self._format_specs_summary(p.specs)}\n\n"
            f"### Đánh giá chuyên môn từ ShopAI\n"
            f"1. **Thẩm định giá bán:** Mức giá **{p.currentPrice:,.0f} đ** tại **{p.platformName}** là mức giá rất cạnh tranh. "
            f"{deal}\n"
            f"2. **Độ an toàn gian hàng:** Sản phẩm có nguồn gốc phân phối rõ ràng, chính sách {p.warranty}, hỗ trợ đổi trả tiêu chuẩn.\n"
            f"3. **Lời khuyên mua sắm:** Bạn có thể bấm vào liên kết trên để xem chi tiết hoặc yêu cầu tôi so sánh sản phẩm này với các đối thủ cùng phân khúc!"
        )

    def _fallback_recommendation(self, context: Dict[str, str], p: ProductItemModel) -> str:
        """Đề xuất sản phẩm xếp hạng #1 kèm bảng tóm tắt các lựa chọn."""
        relaxed_intro = (
            f"> Không tìm thấy sản phẩm khớp 100% yêu cầu của bạn. Dưới đây là các phương án gần nhất sau khi {context['relaxed_search']}.\n\n"
            if context.get("relaxed_search") else ""
        )
        rating_line = (f"{p.rating} / 5.0 ({p.reviewsCount})" if p.rating and p.rating > 0
                       else f"Chưa có đánh giá ({p.reviewsCount})")
        return (
            f"{relaxed_intro}"
            f"### Đề xuất số 1: [{p.name}]({p.externalUrl})\n\n"
            f"- **Nơi bán:** **{p.platformName}** ({p.deliveryTag or 'Chính hãng'})\n"
            f"- **Mức giá ưu đãi:** **{p.currentPrice:,.0f} đ**{_discount_text(p)}\n"
            f"- **Đánh giá người dùng:** {rating_line}\n"
            f"- **Cấu hình nổi bật:** {self._format_specs_summary(p.specs)}\n\n"
            f"### So sánh nhanh Top lựa chọn\n"
            f"{context['products_context']}\n\n"
            f"### Lời khuyên mua sắm từ ShopAI\n"
            f"Mẫu **{p.name}** tại **{p.platformName}** hiện là lựa chọn cân bằng tốt nhất giữa giá cả và cấu hình. "
            f"Bạn có thể nhấn vào liên kết sản phẩm để xem chi tiết hoặc yêu cầu tôi so sánh chuyên sâu hơn."
        )

    @staticmethod
    def _fallback_without_products(context: Dict[str, str]) -> str:
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

    async def generate_response_stream(self, state: AgentState):
        """Lời tư vấn dạng stream (SSE):"""
        context = self.build_standardized_context(state)
        top_prod = state.found_products[0] if state.found_products else None
        if top_prod:
            state.recommended_product = top_prod
        fallback_text = self._build_deterministic_fallback(context, top_prod, intent=state.intent)
        chat_model = get_chat_model(temperature=0.3, fast=True)

        full_text = ""
        if chat_model:
            try:
                async for token in self._stream_llm(chat_model, context, state):
                    full_text += token
                    yield token
            except Exception as e:
                logger.warning(f"[ShoppingAdvisor] Lỗi stream LLM ({e}), tự động chuyển sang Fallback.")
        if not full_text:
            full_text = fallback_text
            async for chunk in _stream_words(fallback_text):
                yield chunk

        state.final_response = full_text.strip()
        state.messages.append(MessageItem(
            id=f"msg-ai-{int(time.time() * 1000)}",
            sender="ai",
            text=state.final_response,
            timestamp="Vừa xong",
            precision="99.0%" if chat_model else "95.0%"
        ))

    @staticmethod
    async def _stream_llm(chat_model, context: Dict[str, str], state: AgentState):
        """Token lời tư vấn của LLM theo prompt advisor."""
        user_prompt = ADVISOR_USER_PROMPT_TEMPLATE.format(
            user_query=context["user_query"],
            criteria_summary=context["criteria_summary"],
            chat_history_context=context.get("chat_history_context", ""),
            products_context=context["products_context"],
            search_notes_context=context.get("search_notes_context", "")
        )
        messages = [
            SystemMessage(content=ADVISOR_SYSTEM_PROMPT + language_instruction(state.language)),
            HumanMessage(content=user_prompt)
        ]
        async for chunk in chat_model.astream(messages):
            token = chunk.content if hasattr(chunk, "content") else str(chunk)
            if token:
                yield token

    async def generate_response(self, state: AgentState) -> AgentState:
        """Sinh phản hồi tư vấn mua sắm hoàn chỉnh (Non-streaming). Tái sử dụng logic stream để đảm bảo tính nhất quán 100%."""
        async for _ in self.generate_response_stream(state):
            pass
        return state
