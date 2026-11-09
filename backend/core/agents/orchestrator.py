import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from integrations.llm import ask_llm, get_chat_model, parse_llm_json
from integrations.platforms import platform_mentioned
from shared.exceptions import LLMError, LLMResponseError

from ..constants import CLARIFY_MAX_QUESTIONS
from ..prompts.language import language_instruction
from ..prompts.router_prompts import ROUTER_SYSTEM_PROMPT
from ..state import AgentState, UniversalSearchCriteria
from .patterns import ADVICE_RE, OUT_OF_SCOPE_RE, SEARCH_ACTION_RE, URL_RE

logger = logging.getLogger("orchestrator")

_FALLBACK_ADVICE_RE = re.compile(
    r"\b(?:n[êe]n\s+mua|c[óo]\s+n[êe]n\s+mua|n[êe]n\s+ch[ọo]n|ph[âa]n\s+v[âa]n|t[ưu]\s+v[ấa]n|ch[àa]o|hello|hi|alo)\b"
)
_PRICE_RE = re.compile(r"(\d+)\s*(triệu|tr|củ)")


def _clarify_round_text(round_: dict) -> str:
    """Đợt hỏi làm rõ đang diễn ra cho router: yêu cầu ban đầu luôn có mặt dù lịch sử chỉ giữ 2 lượt gần nhất."""
    qa = round_.get("qa") or []
    lines = [
        "[Đợt hỏi làm rõ đang diễn ra]",
        f"Yêu cầu ban đầu: {round_.get('request', '')}",
        f"Đã hỏi {round_.get('asked', len(qa))}/{CLARIFY_MAX_QUESTIONS} câu:",
    ]
    for item in qa:
        answer = item.get("answer") or "(chính là yêu cầu hiện tại)"
        lines.append(f"- Hỏi: {item.get('question', '')}\n  Đáp: {answer}")
    return "\n".join(lines)


class OrchestratorAgent:
    """Agent phân loại ý định người dùng và trích xuất tiêu chí đa ngành hàng bằng LLM."""

    async def route(self, state: AgentState) -> AgentState:
        """Link -> parse_link; còn lại hỏi LLM; LLM lỗi / JSON hỏng thì phân loại bằng từ khóa."""
        query = state.user_query.strip()
        url = URL_RE.search(query)
        if url:
            state.intent = "parse_link"
            state.target_link = url.group(0)
            return state

        chat_model = get_chat_model(temperature=0.1, fast=True)
        if chat_model:
            try:
                return await self._llm_route(state, chat_model, query)
            except LLMError as e:
                logger.warning(f"Lỗi khi gọi LLM bóc tách ({e}), chuyển sang phân loại bằng từ khóa.")
        return self._fallback_route(state)

    async def _llm_route(self, state: AgentState, chat_model, query: str) -> AgentState:
        raw = await ask_llm(
            chat_model,
            [
                SystemMessage(content=ROUTER_SYSTEM_PROMPT + language_instruction(state.language)),
                HumanMessage(content=self._router_prompt(state, query)),
            ],
        )
        parsed = parse_llm_json(raw)

        intent = parsed.get("intent", "search_products")
        reply = str(parsed.get("reply") or "").strip()
        if intent == "smalltalk" and reply:
            state.intent = "smalltalk"
            state.final_response = reply
            return state
        if intent == "smalltalk":
            intent = "general_advice"  # thiếu câu trả lời -> để Advisor viết

        state.intent = self._guard_intent(intent, query.lower())
        about_previous = parsed.get("about_previous_products")
        state.about_previous_products = about_previous if isinstance(about_previous, bool) else None
        # Router quyết định luôn việc hỏi làm rõ (không tốn thêm một lần gọi LLM); không điền = không cần hỏi
        clarify = parsed.get("clarify")
        state.clarify_suggestion = clarify if isinstance(clarify, dict) else {"ready": True}
        criteria = parsed.get("criteria", {})
        if criteria:
            try:
                state.criteria = UniversalSearchCriteria(**criteria)
            except (ValidationError, TypeError) as e:
                raise LLMResponseError(f"Tiêu chí LLM trích xuất không hợp lệ: {e}") from e
            logger.info(f"[LLM Extracted] Intent: {state.intent} | Criteria: {state.criteria.model_dump()}")
        return state

    @staticmethod
    def _router_prompt(state: AgentState, query: str) -> str:
        """Câu hỏi kèm lịch sử 2 lượt gần nhất, các sản phẩm đã đề xuất và đợt hỏi làm rõ đang diễn ra (nếu có)."""
        from memory.session_manager import session_memory

        history = session_memory.format_chat_history_for_prompt(state.session_id, max_turns=2)
        previous_products = session_memory.format_previous_products_for_prompt(state.session_id)
        clarify_round = session_memory.get_conversation_state(state.session_id).get("clarify_round")
        context = []
        if history:
            context.append(f"[Lịch sử trao đổi trước đó]:\n{history}")
        if previous_products:
            context.append(previous_products)
        if clarify_round:
            context.append(_clarify_round_text(clarify_round))
        if not context:
            return f"Yêu cầu của người dùng: {query}"
        return "\n\n".join(context) + f"\n\nYêu cầu hiện tại của người dùng: {query}"

    @staticmethod
    def _guard_intent(intent: str, query_lower: str) -> str:
        """Chặn ý định LLM gán sai: ngoài phạm vi; phân vân lựa chọn mà không có hành động tìm mua thì là tư vấn."""
        if intent == "out_of_scope" or OUT_OF_SCOPE_RE.search(query_lower):
            return "out_of_scope"
        if ADVICE_RE.search(query_lower) and not SEARCH_ACTION_RE.search(query_lower):
            return "general_advice"
        return intent

    def _fallback_route(self, state: AgentState) -> AgentState:
        """Cơ chế dự phòng bằng từ khóa khi chưa kết nối được LLM."""
        lower_query = state.user_query.lower()
        state.intent = self._fallback_intent(lower_query)
        state.criteria = (
            None if state.intent == "out_of_scope" else self._fallback_criteria(state.user_query, lower_query)
        )
        return state

    @staticmethod
    def _fallback_intent(q: str) -> str:
        if OUT_OF_SCOPE_RE.search(q):
            return "out_of_scope"
        if _FALLBACK_ADVICE_RE.search(q) and not SEARCH_ACTION_RE.search(q):
            return "general_advice"
        if any(w in q for w in ["so sánh giá", "bảng giá", "giá giữa"]):
            return "compare_products"
        if any(w in q for w in ["voucher", "giảm giá", "khuyến mãi", "deal", "mã"]):
            return "find_deal"
        return "search_products"

    @staticmethod
    def _fallback_criteria(query: str, q: str) -> UniversalSearchCriteria:
        """Tiêu chí tối thiểu từ từ khóa: ngân sách ("30 triệu"), ngành hàng, sàn, phụ kiện hay máy chính."""
        price = _PRICE_RE.search(q)
        if "laptop" in q or "máy tính" in q:
            category, entity = "laptops", "laptop"
        elif "điện thoại" in q or "iphone" in q or "samsung" in q:
            category, entity = "phones", "điện thoại"
        elif "tai nghe" in q or "loa" in q:
            category, entity = "audio", "tai nghe"
        else:
            category, entity = "all", None

        mentioned = platform_mentioned(q)
        # Sàn không hỗ trợ vẫn ghi lại để báo cho người dùng biết
        unsupported = next((s for s in ("lazada", "shopee") if s in q), None)
        platforms = [mentioned.id] if mentioned else ([unsupported] if unsupported else ["all"])

        is_acc = any(
            acc in q
            for acc in [
                "ốp",
                "bao da",
                "cường lực",
                "miếng dán",
                "dán màn",
                "dây sạc",
                "cáp",
                "củ sạc",
                "giá đỡ",
                "chân đế",
                "balo",
                "túi chống sốc",
            ]
        )
        return UniversalSearchCriteria(
            category=category,
            target_entity=None if is_acc else entity,
            is_accessory=is_acc,
            max_price=float(price.group(1)) * 1_000_000 if price else None,
            target_platforms=platforms,
            cleaned_query=query,
        )
