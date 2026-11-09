"""Hỏi làm rõ do router (LLM) đề xuất ngay trong lần hiểu câu hỏi: tối đa 3 câu, mỗi lượt một câu,
đủ thông tin thì tìm luôn (chạy offline, router giả)."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from core.agents import orchestrator as orchestrator_module
from core.agents.orchestrator import OrchestratorAgent
from core.constants import SKIP_OPTION
from core.flows import clarification
from core.state import AgentState, UniversalSearchCriteria
from memory.session_manager import SessionMemoryManager

LAPTOP = UniversalSearchCriteria(
    category="laptops", product_type="laptop", target_entity="laptop", cleaned_query="laptop"
)

ASK_USAGE = {
    "known_usage": None,
    "ready": False,
    "field": "usage",
    "question": "Bạn dùng laptop chủ yếu để làm gì?",
    "hint": "Mục đích quyết định cấu hình cần có.",
    "options": ["Học tập, văn phòng", "Lập trình", "Đồ họa", "Chơi game"],
}
ASK_BUDGET = {
    "ready": False,
    "field": "budget",
    "question": "Ngân sách của bạn khoảng bao nhiêu?",
    "options": ["Dưới 15 triệu", "15 - 25 triệu"],
}
READY = {"ready": True}


@pytest.fixture
def memory(monkeypatch):
    mem = SessionMemoryManager()
    monkeypatch.setattr(mem, "_run_in_background", lambda coro: coro.close())  # không ghi CSDL thật
    monkeypatch.setattr(clarification, "session_memory", mem)
    return mem


def _turn(sid, query, criteria, suggestion, intent="search_products"):
    """Một lượt như node clarify của graph; `suggestion` là phần "clarify" router trả về (None = router không có LLM)."""
    state = AgentState(
        session_id=sid, user_query=query, intent=intent, criteria=criteria, clarify_suggestion=suggestion
    )
    clarification.apply_pending(state)
    clarification.decide(state)
    return state


def test_asks_one_question_then_searches_when_enough(memory):
    s1 = _turn("c1", "tìm laptop", LAPTOP, ASK_USAGE)
    clar = s1.clarification
    assert clar["field"] == "usage" and s1.final_response == ASK_USAGE["question"]
    assert [o["label"] for o in clar["options"]][:4] == ASK_USAGE["options"]
    assert clar["options"][-1]["value"] == SKIP_OPTION and clar["skip_value"] == SKIP_OPTION
    assert clar["context_hint"].startswith("Câu hỏi 1/3")

    # Trả lời câu 1 -> router thấy đủ -> tìm luôn, không hỏi thêm
    s2 = _turn("c1", "lập trình", UniversalSearchCriteria(usage_purpose="lập trình"), READY, intent="general_advice")
    assert s2.clarification is None and s2.intent == "search_products"
    assert s2.criteria.cleaned_query == "laptop" and s2.criteria.usage_purpose == "lập trình"
    assert "clarify_round" not in memory.get_conversation_state("c1")


def test_round_records_questions_and_answers(memory):
    _turn("c1b", "tìm laptop", LAPTOP, ASK_USAGE)
    _turn("c1b", "lập trình", UniversalSearchCriteria(usage_purpose="lập trình"), ASK_BUDGET, intent="general_advice")
    round_ = memory.get_conversation_state("c1b")["clarify_round"]
    assert round_["request"] == "tìm laptop" and round_["asked"] == 2
    assert round_["qa"][0] == {"question": ASK_USAGE["question"], "answer": "lập trình"}
    assert round_["qa"][1] == {"question": ASK_BUDGET["question"]}


def test_never_more_than_three_questions(memory):
    s = _turn("c2", "tìm laptop", LAPTOP, ASK_USAGE)  # router lúc nào cũng muốn hỏi tiếp
    asked = 1
    for answer in ("học tập", "màn to", "pin lâu"):
        assert s.clarification is not None
        s = _turn("c2", answer, UniversalSearchCriteria(), ASK_USAGE, intent="general_advice")
        asked += s.clarification is not None
    assert s.clarification is None and s.intent == "search_products" and asked == 3


def test_answer_that_makes_request_specific_searches(memory):
    _turn("c3", "tìm laptop lập trình", LAPTOP.model_copy(update={"usage_purpose": "lập trình"}), ASK_BUDGET)
    s = _turn(
        "c3",
        "15 - 25 triệu",
        UniversalSearchCriteria(min_price=15e6, max_price=25e6),
        ASK_BUDGET,
        intent="general_advice",
    )
    assert s.clarification is None and s.criteria.max_price == 25e6


def test_budget_plus_known_usage_searches_even_if_router_wants_more(memory):
    with_budget = LAPTOP.model_copy(update={"cleaned_query": "laptop gaming", "max_price": 30e6})
    s = _turn("c3b", "laptop gaming dưới 30 triệu", with_budget, {**ASK_USAGE, "known_usage": "chơi game"})
    assert s.clarification is None


def test_skip_option_searches_immediately(memory):
    _turn("c4", "tìm laptop", LAPTOP, ASK_USAGE)
    s = _turn("c4", SKIP_OPTION, UniversalSearchCriteria(), ASK_USAGE, intent="general_advice")
    assert s.clarification is None and s.intent == "search_products"


def test_specific_request_needs_no_question(memory):
    s = _turn("c5", "tìm iphone 15", UniversalSearchCriteria(category="phones", product_type="iPhone 15"), ASK_USAGE)
    assert s.clarification is None


def test_router_without_llm_falls_back_to_budget_question(memory):
    s = _turn("c6", "tìm laptop", LAPTOP, None)
    assert s.clarification and s.clarification["field"] == "budget"


def test_same_category_not_asked_again_after_round(memory):
    _turn("c7", "tìm laptop", LAPTOP, ASK_USAGE)
    _turn("c7", "chơi game", UniversalSearchCriteria(usage_purpose="chơi game"), READY, intent="general_advice")
    s = _turn("c7", "tìm laptop khác", LAPTOP, ASK_USAGE)
    assert s.clarification is None


# ---------------------------------------------------------------- router trả luôn quyết định hỏi làm rõ
class FakeRouter:
    def __init__(self, payload):
        self.payload, self.prompts = payload, []

    async def ainvoke(self, messages):
        self.prompts.append(messages[1].content)
        return SimpleNamespace(content=json.dumps(self.payload, ensure_ascii=False))


def _route(monkeypatch, payload, conversation_state=None):
    from memory.session_manager import session_memory

    router = FakeRouter(payload)
    monkeypatch.setattr(orchestrator_module, "get_chat_model", lambda **_: router)
    monkeypatch.setattr(session_memory, "get_conversation_state", lambda sid: conversation_state or {})
    state = asyncio.run(OrchestratorAgent().route(AgentState(session_id="route-clar", user_query="tìm laptop")))
    return state, router


SEARCH = {"intent": "search_products", "criteria": {"category": "laptops", "target_entity": "laptop"}}


def test_router_passes_clarify_suggestion_through(monkeypatch):
    state, _ = _route(monkeypatch, {**SEARCH, "clarify": ASK_USAGE})
    assert state.clarify_suggestion == ASK_USAGE


def test_router_without_clarify_means_ready(monkeypatch):
    state, _ = _route(monkeypatch, SEARCH)
    assert state.clarify_suggestion == {"ready": True}


def test_router_prompt_includes_active_round(monkeypatch):
    round_ = {"category": "laptops", "request": "tìm laptop", "asked": 1, "qa": [{"question": ASK_USAGE["question"]}]}
    _, router = _route(monkeypatch, {**SEARCH, "clarify": READY}, {"clarify_round": round_})
    prompt = router.prompts[0]
    assert "[Đợt hỏi làm rõ đang diễn ra]" in prompt and "Yêu cầu ban đầu: tìm laptop" in prompt
    assert "Đã hỏi 1/3 câu" in prompt and ASK_USAGE["question"] in prompt
