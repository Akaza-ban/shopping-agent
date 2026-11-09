"""Dựng ngữ cảnh (các khối chữ) đưa vào prompt của Shopping Advisor từ AgentState.

build_context(state) trả về dict điền vào ADVISOR_USER_PROMPT_TEMPLATE:
user_query, scope_note, criteria_summary, chat_history_context, products_context, search_notes_context
(+ searched, relaxed_search, total_found cho câu trả lời dựng sẵn khi LLM lỗi).
"""

from typing import Any

from integrations.platforms import display_names
from memory.session_manager import session_memory
from services.catalog.reviews import rating_text
from shared.spec_rows import PREFERRED_SPEC_ROWS

from ..state import AgentState, ProductItemModel, UniversalSearchCriteria

DEFAULT_SPECS = "Chưa có thông số"
UNKNOWN = "Chưa rõ"
MAX_SPEC_ITEMS = 7
MAX_SPEC_VALUE_CHARS = 70
MAX_SPEC_TEXT_CHARS = 120
MAX_PRODUCTS_IN_PROMPT = 3
HISTORY_TURNS = 3
SEARCH_INTENTS = ("search_products", "compare_products", "find_deal")


def format_specs_summary(specs: Any) -> str:
    """Thông số kỹ thuật -> một dòng ngắn (ưu tiên các hàng quan trọng: CPU, RAM, màn hình...)."""
    if not specs:
        return DEFAULT_SPECS
    if isinstance(specs, dict):
        ordered_keys = [k for k in PREFERRED_SPEC_ROWS if specs.get(k)] + [
            k for k in specs if k not in PREFERRED_SPEC_ROWS
        ]
        items = []
        for k in ordered_keys:
            v = specs.get(k)
            if k and v:
                items.append(f"{k}: {str(v)[:MAX_SPEC_VALUE_CHARS]}")
            if len(items) >= MAX_SPEC_ITEMS:
                break
        return " | ".join(items) if items else DEFAULT_SPECS
    text = str(specs).strip()
    if len(text) > MAX_SPEC_TEXT_CHARS:
        text = text[:MAX_SPEC_TEXT_CHARS] + "..."
    return text or DEFAULT_SPECS


def format_product(idx: int, p: ProductItemModel) -> str:
    """Một sản phẩm -> bản tóm tắt vài dòng cho LLM (giá, đánh giá, cấu hình, bảo hành, link)."""
    savings = max(0, p.originalPrice - p.currentPrice)
    discount = f" (Giảm {p.discountPercent}%, tiết kiệm {savings:,.0f} đ)" if p.discountPercent > 0 else ""
    reasons = "; ".join(p.matchReasons) if p.matchReasons else "không có"
    return (
        f"[Lựa chọn #{idx}] Điểm phù hợp: {p.aiMatchScore}/100 (lý do: {reasons})\n"
        f"- Tên & Sàn: {p.name} (Bán tại: {p.platformName})\n"
        f"- Giá ưu đãi: {p.currentPrice:,.0f} đ{discount} | Đánh giá: {rating_text(p.rating, p.reviewsCount)}\n"
        f"- Cấu hình ({'đã đọc trang chi tiết' if p.detailFetched else 'chỉ từ trang danh sách'}): {format_specs_summary(p.specs)}\n"
        f"- Bảo hành: {p.warranty or UNKNOWN} | Đổi trả: {p.returnPolicy or UNKNOWN} | Vận chuyển: {p.deliveryTag or UNKNOWN}\n"
        f"- Link: {p.externalUrl or 'không có'}"
    )


def format_products(
    products: list[ProductItemModel], max_items: int = MAX_PRODUCTS_IN_PROMPT, searched: bool = False
) -> str:
    """Khối sản phẩm; không có sản phẩm thì nói rõ là đã quét mà không thấy, hay lượt này không quét."""
    if not products:
        if searched:
            return (
                f"KHÔNG TÌM THẤY SẢN PHẨM: hệ thống đã quét các sàn ({display_names()}) "
                "và kho dữ liệu nhưng không có sản phẩm nào phù hợp, kể cả sau khi đã thử nới lỏng tiêu chí. "
                "Không có dữ liệu giá nào để trích dẫn."
            )
        return "Lượt này không quét sàn (câu hỏi tư vấn định hướng). Chỉ tư vấn kiến thức chuyên môn, không nêu giá cụ thể."
    return "\n\n".join(format_product(i, p) for i, p in enumerate(products[:max_items], 1))


def format_criteria(criteria: UniversalSearchCriteria | None) -> str:
    """Ràng buộc của người dùng (ngành hàng, hãng, ngân sách, mục đích)."""
    if not criteria:
        return ""
    parts = []
    # "Khác" không cho LLM thêm thông tin gì, lại dễ bị hiểu là ngoài phạm vi tư vấn
    if criteria.category and criteria.category not in ("all", "other"):
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


def scope_note(intent: str | None) -> str:
    """Kết luận phạm vi của bộ phân loại: Advisor không tự phán lại (dễ từ chối nhầm câu hỏi mua sắm ngắn, mơ hồ)."""
    if intent == "out_of_scope":
        return "Bộ phân loại đã xác định: câu hỏi NGOÀI phạm vi mua sắm -> áp dụng Trường hợp 4."
    if intent:
        return "Bộ phân loại đã xác định: câu hỏi THUỘC phạm vi mua sắm -> KHÔNG áp dụng Trường hợp 4, không từ chối."
    return ""


def _search_notes(state: AgentState) -> str:
    """Ghi chú cho LLM: tiêu chí đã nới lỏng, kết quả so sánh, độ tin cậy của dữ liệu."""
    parts = []
    if state.relaxed_search:
        parts.append(f"Tiêu chí đã nới lỏng: {state.relaxed_search} (không có sản phẩm khớp 100% yêu cầu gốc).")
    if state.comparison_summary:
        parts.append(f"Kết quả công cụ so sánh: {state.comparison_summary}")
    if state.comparison_markdown:
        parts.append(
            "Bảng so sánh do công cụ tạo (ô in đậm là tốt nhất của hàng; giao diện đã hiển thị bảng này, "
            "chỉ cần tóm tắt điểm khác biệt chính):\n" + state.comparison_markdown
        )
    if state.search_notes:
        parts.append("Ghi chú độ tin cậy:\n" + "\n".join(f"- {n}" for n in state.search_notes))
    return "\n".join(parts)


def build_context(state: AgentState) -> dict[str, str]:
    """Toàn bộ ngữ cảnh đầu vào của Advisor cho lượt này."""
    searched = state.intent in SEARCH_INTENTS
    products = state.found_products
    # Chỉ dùng lại sản phẩm lượt trước khi câu hỏi nói về chúng (đổi chủ đề thì không đề xuất hàng cũ)
    if not products and not searched and state.session_id and state.about_previous_products is not False:
        last = session_memory.get_last_products(state.session_id)
        if last:
            products = [ProductItemModel(**p) for p in last]

    products_context = format_products(products, searched=searched)
    if products and products is not state.found_products:
        products_context = (
            "Câu hỏi này nói tiếp về các sản phẩm ĐÃ ĐỀ XUẤT ở lượt trước (dưới đây): "
            "trả lời dựa trên đúng các sản phẩm này.\n\n" + products_context
        )

    history = (
        session_memory.format_chat_history_for_prompt(state.session_id, max_turns=HISTORY_TURNS)
        if state.session_id
        else ""
    )
    return {
        "user_query": state.user_query,
        "scope_note": scope_note(state.intent),
        "criteria_summary": format_criteria(state.criteria),
        "chat_history_context": f"[Lịch sử trao đổi trước đó]:\n{history}" if history else "",
        "products_context": products_context,
        "search_notes_context": _search_notes(state),
        "searched": "1" if searched else "",
        "relaxed_search": state.relaxed_search or "",
        "total_found": str(len(products)),
    }
