"""Hỏi làm rõ trước khi cào khi yêu cầu tìm mua còn thiếu thông tin, rồi gộp câu trả lời vào tiêu chí.

Router (LLM) quyết định hỏi gì ngay trong lần gọi hiểu câu hỏi (state.clarify_suggestion, không tốn thêm lần gọi);
decide() áp quy tắc: mỗi lượt tối đa MỘT câu, cả đợt tối đa MAX_QUESTIONS câu; sau mỗi câu trả lời router xét lại,
đủ thông tin thì tìm ngay, không hỏi tiếp.

Lượt 1: "tìm laptop"            -> router đề xuất "Bạn dùng laptop chủ yếu để làm gì?" -> decide() hỏi (câu 1/3)
Lượt 2: "lập trình"             -> apply_pending() gộp câu trả lời; router đề xuất hỏi ngân sách (câu 2/3)
Lượt 3: "khoảng 20 triệu"       -> apply_pending(); đã có ngân sách + mục đích -> tìm kiếm
Người dùng bảo "cứ tìm" / đổi chủ đề / đã hỏi đủ 3 câu -> tìm luôn.
Router không dùng được LLM -> maybe_ask(): chỉ hỏi ngân sách theo quy tắc, một lần.

Trạng thái hội thoại: pending_clarification (tiêu chí đang chờ), clarify_round (đợt hỏi đang diễn ra:
ngành hàng, yêu cầu ban đầu, các câu đã hỏi và câu trả lời), clarified_categories (ngành đã hỏi, không hỏi lại).
"""

import logging
import re
import time
from typing import Any

from memory.session_manager import session_memory

from ..constants import (
    BUDGET_OPTIONS,
    CLARIFY_MAX_QUESTIONS,
    DEFAULT_BUDGET_OPTIONS,
    SKIP_BUDGET_OPTION,
    SKIP_OPTION,
    SKIP_PATTERN,
)
from ..i18n import tr
from ..state import AgentState, UniversalSearchCriteria

logger = logging.getLogger("clarification")

MAX_QUESTIONS = CLARIFY_MAX_QUESTIONS
MAX_OPTIONS = 5
MAX_OPTION_CHARS = 60
MAX_QUESTION_CHARS = 200
FIELDS = ("budget", "usage", "size", "type", "brand", "other")

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
        return tr(
            "clarify.budget_under" if m.group(1) == "Dưới" else "clarify.budget_over", language, amount=m.group(2)
        )
    m = _RANGE_RE.fullmatch(option)
    if m:
        return tr("clarify.budget_range", language, low=m.group(1), high=m.group(2))
    return option


def budget_clarification(question: str, category: str, language: str) -> dict[str, Any]:
    """Câu hỏi ngân sách kèm các lựa chọn theo ngành hàng (giao diện hiển thị thành nút bấm)."""
    options = BUDGET_OPTIONS.get(category, DEFAULT_BUDGET_OPTIONS) + [SKIP_BUDGET_OPTION]
    return {
        "id": f"clar-budget-{int(time.time() * 1000)}",
        "field": "budget",
        "question": question,
        "context_hint": tr("clarify.context_hint", language),
        "options": [{"id": f"opt-{i}", "label": budget_label(o, language), "value": o} for i, o in enumerate(options)],
        "allow_custom_input": True,
        "skip_value": SKIP_BUDGET_OPTION,  # nút "Bỏ qua" gửi câu này: tìm luôn, không hỏi lại
    }


def _is_purchase(state: AgentState, c: UniversalSearchCriteria) -> bool:
    """Yêu cầu tìm mua: ý định tìm sản phẩm, hoặc xin tư vấn nhưng nói rõ "tìm / mua" (chưa có sản phẩm lượt trước)."""
    wants_to_buy = (
        state.intent == "general_advice"
        and c.target_entity
        and _BUY_RE.search(state.user_query)
        and not session_memory.get_last_products(state.session_id)
    )
    return state.intent == "search_products" or bool(wants_to_buy)


def is_vague_purchase(state: AgentState, c: UniversalSearchCriteria) -> bool:
    """Yêu cầu tìm mua chưa có giá, hãng, model cụ thể và người dùng không bảo "cứ tìm"."""
    if not _is_purchase(state, c):
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
    conv = session_memory.get_conversation_state(state.session_id)
    pending = conv.get("pending_clarification")
    if not pending:
        return
    session_memory.update_conversation_state(state.session_id, pending_clarification=None)
    if state.intent in ("parse_link", "out_of_scope"):
        session_memory.update_conversation_state(state.session_id, clarify_round=None)
        return
    new = state.criteria
    new_cat = (new.category if new else None) or "all"
    if new and new_cat not in ("all", pending.get("category")) and (new.product_type or new.target_entity):
        session_memory.update_conversation_state(state.session_id, clarify_round=None)
        return  # chủ đề mới

    round_ = conv.get("clarify_round")
    if round_ and round_.get("qa"):
        qa = [dict(item) for item in round_["qa"]]
        qa[-1]["answer"] = state.user_query
        session_memory.update_conversation_state(state.session_id, clarify_round={**round_, "qa": qa})

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


# ---------------------------------------------------------------- LLM quyết định hỏi gì
def _is_specific(state: AgentState, c: UniversalSearchCriteria) -> bool:
    """Rõ ràng đủ để tìm, khỏi tốn một lần gọi LLM: nêu model cụ thể, hoặc có ngân sách kèm mục đích / hãng."""
    if re.search(r"\d", f"{c.product_type or ''} {c.cleaned_query or ''}"):
        return True
    return bool((c.max_price or c.min_price) and (c.usage_purpose or c.brands))


def _parse_question(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Phản hồi LLM -> {"field", "question", "hint", "options"}; None = đủ thông tin hoặc phản hồi không dùng được."""
    if raw.get("ready") is not False:
        return None
    question = str(raw.get("question") or "").strip()[:MAX_QUESTION_CHARS]
    if not question:
        return None
    options = [str(o).strip()[:MAX_OPTION_CHARS] for o in (raw.get("options") or []) if str(o).strip()]
    field = str(raw.get("field") or "other")
    return {
        "field": field if field in FIELDS else "other",
        "question": question,
        "hint": str(raw.get("hint") or "").strip()[:MAX_QUESTION_CHARS],
        "options": list(dict.fromkeys(options))[:MAX_OPTIONS],
    }


def _router_decision(state: AgentState) -> dict[str, Any] | None:
    """Quyết định của router (state.clarify_suggestion): {"ready": True} hoặc câu hỏi tiếp theo.

    None khi router không dùng được LLM (đã phân loại bằng từ khóa) -> bên gọi dùng câu hỏi ngân sách theo quy tắc.
    """
    raw = state.clarify_suggestion
    if raw is None:
        return None
    # Đã có ngân sách và biết mục đích (kể cả suy ra từ từ khóa) thì tìm luôn, dù LLM còn muốn hỏi đào sâu
    c = state.criteria
    if (c.max_price or c.min_price) and str(raw.get("known_usage") or "").strip():
        return {"ready": True}
    question = _parse_question(raw)
    return {"ready": True} if question is None else {"ready": False, **question}


def llm_clarification(question: dict[str, Any], step: int, language: str) -> dict[str, Any]:
    """Câu hỏi LLM đặt -> dạng giao diện hiển thị (nút bấm); cuối luôn có lựa chọn "cứ tìm"."""
    options = [{"id": f"opt-{i}", "label": o, "value": o} for i, o in enumerate(question["options"])]
    options.append({"id": f"opt-{len(options)}", "label": tr("clarify.skip", language), "value": SKIP_OPTION})
    step_text = tr("clarify.step", language, step=step, total=MAX_QUESTIONS)
    return {
        "id": f"clar-{question['field']}-{int(time.time() * 1000)}",
        "field": question["field"],
        "question": question["question"],
        "context_hint": f"{step_text}. {question['hint']}" if question["hint"] else step_text,
        "options": options,
        "allow_custom_input": True,
        "skip_value": SKIP_OPTION,
    }


def _finish(state: AgentState) -> None:
    session_memory.update_conversation_state(state.session_id, clarify_round=None)


def decide(state: AgentState) -> None:
    """Hỏi thêm một câu (state.clarification + state.final_response) hoặc để luồng đi tìm kiếm.

    Gọi sau apply_pending(). Câu hỏi do router đặt sẵn trong cùng lần gọi LLM (state.clarify_suggestion), ở đây chỉ
    áp các quy tắc. Không hỏi khi: không phải yêu cầu tìm mua, người dùng bảo "cứ tìm", đã hỏi đủ MAX_QUESTIONS câu,
    ngành hàng đã hỏi xong trước đó, yêu cầu đã đủ cụ thể, hoặc router thấy đã đủ thông tin.
    """
    c = state.criteria
    if not c or not _is_purchase(state, c):
        _finish(state)
        return
    conv = session_memory.get_conversation_state(state.session_id)
    category = c.category or "all"
    round_ = conv.get("clarify_round")
    in_round = bool(round_) and round_.get("category") == category
    asked_categories = list(conv.get("clarified_categories") or [])
    if not in_round and category in asked_categories:
        return
    asked = int(round_.get("asked", 0)) if in_round else 0
    if asked >= MAX_QUESTIONS or SKIP_PATTERN.search(state.user_query) or _is_specific(state, c):
        _finish(state)
        return

    request = round_.get("request") if in_round else state.user_query
    qa = list(round_.get("qa") or []) if in_round else []
    decision = _router_decision(state)
    if decision is None:
        if not in_round:
            maybe_ask(state)  # không dùng được LLM: chỉ hỏi ngân sách theo quy tắc
        else:
            _finish(state)
        return
    if decision["ready"]:
        logger.info(f"[Clarification] Đủ thông tin sau {asked} câu hỏi, chuyển sang tìm kiếm")
        _finish(state)
        return

    state.clarification = llm_clarification(decision, asked + 1, state.language)
    state.final_response = decision["question"]
    state.intent = "search_products"
    session_memory.update_conversation_state(
        state.session_id,
        pending_clarification=c.model_dump(),
        clarified_categories=asked_categories if category in asked_categories else asked_categories + [category],
        clarify_round={
            "category": category,
            "request": request,
            "asked": asked + 1,
            "qa": qa + [{"question": decision["question"]}],
        },
    )
    logger.info(f"[Clarification] Câu hỏi {asked + 1}/{MAX_QUESTIONS} ({decision['field']}): {decision['question']}")
