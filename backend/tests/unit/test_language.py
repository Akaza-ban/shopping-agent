"""
Ngôn ngữ trả lời theo Cài đặt người dùng: câu hỏi làm rõ, mức ngân sách, câu hỏi gợi ý và chỉ dẫn cho LLM.
"""
from core.prompts.language import language_instruction
from core.constants import SKIP_BUDGET_OPTION
from core.flows import clarification, suggestions
from core.state import AgentState, ProductItemModel, UniversalSearchCriteria
from src.schemas.chat import ChatRequest


def test_chat_request_language_defaults_to_vietnamese():
    assert ChatRequest(message="laptop").language == "vi"
    assert ChatRequest(message="laptop", language="en").language == "en"


def test_language_instruction():
    assert language_instruction("vi") == ""
    assert "English" in language_instruction("en")


def test_budget_labels_translated_but_values_kept():
    label = clarification.budget_label
    assert label("Dưới 15 triệu", "en") == "Under 15 million VND"
    assert label("15 - 20 triệu", "en") == "15–20 million VND"
    assert label("Trên 30 triệu", "en") == "Over 30 million VND"
    assert label(SKIP_BUDGET_OPTION, "en") == "No budget limit, just search"
    assert label("Dưới 15 triệu", "vi") == "Dưới 15 triệu"


def _clarify(language):
    state = AgentState(
        session_id=f"test-lang-{language}", user_query="tìm laptop gaming", language=language,
        intent="search_products",
        criteria=UniversalSearchCriteria(category="laptops", product_type="laptop gaming", target_entity="laptop"),
    )
    clarification.maybe_ask(state)
    return state.clarification


def test_clarification_in_english_keeps_vietnamese_values():
    clar = _clarify("en")
    assert clar["question"].startswith("Roughly how much")
    first = clar["options"][0]
    assert first["label"] == "Under 15 million VND" and first["value"] == "Dưới 15 triệu"


def test_clarification_in_vietnamese():
    clar = _clarify("vi")
    assert clar["question"].startswith("Bạn dự định chi")
    assert clar["options"][0]["label"] == clar["options"][0]["value"]


def test_suggested_questions_follow_language():
    products = [
        ProductItemModel(id=f"p{i}", name=f"Laptop Model {i}", platform="tiki", platformName="Tiki",
                         currentPrice=20_000_000, originalPrice=20_000_000)
        for i in range(2)
    ]
    en = suggestions.generate(AgentState(session_id="s-en", user_query="laptop", language="en", found_products=products))
    vi = suggestions.generate(AgentState(session_id="s-vi", user_query="laptop", found_products=products))
    assert en[0].startswith("Compare") and vi[0].startswith("So sánh")
