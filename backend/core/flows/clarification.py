"""Hỏi làm rõ ngân sách trước khi cào khi yêu cầu tìm mua còn quá chung, rồi gộp câu trả lời vào tiêu chí.

Lượt 1: "tìm laptop gaming"  -> maybe_ask(): hỏi ngân sách, lưu tiêu chí đang chờ vào trạng thái hội thoại.
Lượt 2: "20 - 25 triệu"      -> apply_pending(): gộp khoảng giá vào tiêu chí đang chờ rồi tìm.
Mỗi ngành hàng chỉ hỏi một lần trong một hội thoại.
"""
import logging
import re
import time
from typing import Any, Dict

from memory.session_manager import session_memory

from ..constants import BUDGET_OPTIONS, DEFAULT_BUDGET_OPTIONS, SKIP_BUDGET_OPTION, SKIP_PATTERN
from ..i18n import tr
from ..state import AgentState, UniversalSearchCriteria

logger = logging.getLogger("clarification")

_UNDER_OVER_RE = re.compile(r"(Dưới|Trên) (\d+) triệu")
_RANGE_RE = re.compile(r"(\d+) - (\d+) triệu")
_BUY_RE = re.compile(r"\b(?:tìm|mua)\b", re.IGNORECASE)
# Trường của câu trả lời được gộp vào tiêu chí đang chờ; giá trị rỗng / mặc định thì bỏ qua
_MERGED_FIELDS = ("min_price", "max_price", "usage_purpose", "priority")
_EMPTY_VALUES = (None, "", "best_value")


def budget_label(option: str, language: str) -> str:
    """Nhãn hiển thị của mức ngân sách theo ngôn ngữ; giá trị gửi lại vẫn là câu tiếng Việt gốc."""
    if language != "en":
        return option
    if option == SKIP_BUDGET_OPTION:
        return tr("clarify.budget_skip", language)
    m = _UNDER_OVER_RE.fullmatch(option)
    if m:
        return tr("clarify.budget_under" if m.group(1) == "Dưới" else "clarify.budget_over", language, amount=m.group(2))
    m = _RANGE_RE.fullmatch(option)
    if m:
        return tr("clarify.budget_range", language, low=m.group(1), high=m.group(2))
    return option


def budget_clarification(question: str, category: str, language: str) -> Dict[str, Any]:
    """Câu hỏi ngân sách kèm các lựa chọn theo ngành hàng (giao diện hiển thị thành nút bấm)."""
    options = BUDGET_OPTIONS.get(category, DEFAULT_BUDGET_OPTIONS) + [SKIP_BUDGET_OPTION]
    return {
        "id": f"clar-budget-{int(time.time() * 1000)}",
        "field": "budget",
        "question": question,
        "context_hint": tr("clarify.context_hint", language),
        "options": [{"id": f"opt-{i}", "label": budget_label(o, language), "value": o} for i, o in enumerate(options)],
        "allow_custom_input": True,
    }


def is_vague_purchase(state: AgentState, c: UniversalSearchCriteria) -> bool:
    """Yêu cầu tìm mua chưa có giá, hãng, model cụ thể và người dùng không bảo "cứ tìm"."""
    wants_to_buy = (
        state.intent == "general_advice"
        and c.target_entity
        and _BUY_RE.search(state.user_query)
        and not session_memory.get_last_products(state.session_id)
    )
    if state.intent != "search_products" and not wants_to_buy:
        return False
    if c.max_price or c.min_price or c.brands:
        return False
    product_text = f"{c.product_type or ''} {c.cleaned_query or ''}"
    return not (re.search(r"\d", product_text) or SKIP_PATTERN.search(state.user_query))


def maybe_ask(state: AgentState) -> None:
    """Đặt state.clarification + câu hỏi vào state.final_response nếu cần hỏi ngân sách trước khi cào."""
    c = state.criteria
    if not c or not is_vague_purchase(state, c):
        return
    category = c.category or "all"
    asked = list(session_memory.get_conversation_state(state.session_id).get("clarified_categories") or [])
    if category in asked:
        return

    language = state.language
    entity = c.product_type or c.target_entity or tr("clarify.default_entity", language)
    question = tr("clarify.budget_question", language, entity=entity)
    state.clarification = budget_clarification(question, category, language)
    purpose_hint = "" if c.usage_purpose else tr("clarify.purpose_hint", language)
    state.final_response = f"{question}{purpose_hint}"
    state.intent = "search_products"
    session_memory.update_conversation_state(
        state.session_id,
        pending_clarification=c.model_dump(),
        clarified_categories=asked + [category],
    )
    logger.info(f"[Clarification] Hỏi ngân sách cho '{entity}' (session={state.session_id})")


def apply_pending(state: AgentState) -> None:
    """Lượt trước vừa hỏi làm rõ -> gộp câu trả lời (VD "20 - 25 triệu") vào tiêu chí đang chờ.

    Người dùng chuyển sang chủ đề / ngành hàng khác thì bỏ tiêu chí đang chờ.
    """
    pending = session_memory.get_conversation_state(state.session_id).get("pending_clarification")
    if not pending:
        return
    session_memory.update_conversation_state(state.session_id, pending_clarification=None)
    if state.intent in ("parse_link", "out_of_scope"):
        return
    new = state.criteria
    new_cat = (new.category if new else None) or "all"
    if new and new_cat not in ("all", pending.get("category")) and (new.product_type or new.target_entity):
        return  # chủ đề mới

    merged = dict(pending)
    if new:
        for field in _MERGED_FIELDS:
            value = getattr(new, field)
            if value not in _EMPTY_VALUES:
                merged[field] = value
        if new.brands:
            merged["brands"] = new.brands
        if new.attributes:
            merged["attributes"] = {**(pending.get("attributes") or {}), **new.attributes}
        if new.target_platforms and new.target_platforms != ["all"]:
            merged["target_platforms"] = new.target_platforms
    state.criteria = UniversalSearchCriteria(**merged)
    state.intent = "search_products"
    logger.info(
        f"[Clarification] Gộp câu trả lời vào tiêu chí: max_price={state.criteria.max_price}, "
        f"min_price={state.criteria.min_price}, usage={state.criteria.usage_purpose}"
    )
