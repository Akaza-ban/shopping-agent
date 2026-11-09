"""
Các lỗi tìm thấy khi đọc lại cuộc hội thoại "MSI Katana hay Acer Nitro 5" (chạy offline, không gọi LLM thật):
1. Mục đích "gaming" bị coi là thông số bắt buộc -> máy gaming không có chữ "Gaming" trong tên bị trừ điểm.
2. Tìm phụ kiện bỏ qua bộ lọc ngữ nghĩa -> "USB Bluetooth ... - miếng lót chuột" lọt vào kết quả lót chuột.
3. "Đã bán N" bị coi là N lượt đánh giá (cả khi chấm điểm lẫn khi đưa cho LLM).
4. Lời đề nghị ở cuối câu trả lời bị cắt khỏi lịch sử -> "có" không được hiểu.
8. Đổi chủ đề vẫn đề xuất sản phẩm của chủ đề cũ.
"""

import asyncio
import json
from types import SimpleNamespace

from core.agents import advisor_context
from core.state import AgentState, MessageItem, UniversalSearchCriteria
from memory.session_manager import session_memory
from services.catalog import spec_fit
from services.catalog.ranker import score_product
from services.catalog.reviews import rating_text, review_count


# ---------------------------------------------------------------- 1. mục đích không phải thông số
def test_usage_in_attributes_moves_to_usage_purpose():
    c = UniversalSearchCriteria(
        category="laptops", usage_purpose="chơi game", attributes={"usage": "gaming", "gpu": "RTX 4050"}
    )
    assert c.attributes == {"gpu": "RTX 4050"} and c.usage_purpose == "chơi game"
    c = UniversalSearchCriteria(attributes={"usage_purpose": "gaming"})
    assert c.attributes == {} and c.usage_purpose == "gaming"
    # "type" là thông số thật của tai nghe; hãng ghi nhầm vào attributes thì chuyển sang brands
    c = UniversalSearchCriteria(attributes={"type": "chụp tai", "brand": "Sony"})
    assert c.attributes == {"type": "chụp tai"} and c.brands == ["Sony"]


def test_gaming_laptop_without_gaming_in_name_is_not_penalised():
    criteria = UniversalSearchCriteria(category="laptops", usage_purpose="chơi game", attributes={"usage": "gaming"})
    katana = {
        "name": "Laptop MSI Katana 15 HX B14WEK-286VN",
        "currentPrice": 34_990_000,
        "rating": 5.0,
        "reviewsCount": "6 đánh giá",
        "specs": {"Loại card đồ họa": "NVIDIA GeForce RTX 5050"},
    }
    score, reasons, status = score_product(katana, criteria)
    assert status == {} and not any("Chưa xác minh" in r for r in reasons)


# ---------------------------------------------------------------- 3. đã bán khác đánh giá
def test_sold_count_is_not_a_review_count():
    assert review_count("Đã bán 46575") == 0 and review_count("348 đánh giá") == 348
    assert rating_text(5, "Đã bán 46575") == "5/5 (sàn không ghi số lượt đánh giá; Đã bán 46575)"
    assert rating_text(4.9, "348 đánh giá") == "4.9/5 (348 đánh giá)"
    sold = {"name": "Tấm lót chuột", "currentPrice": 59_000, "rating": 5.0, "reviewsCount": "Đã bán 46575"}
    reviewed = {**sold, "rating": 4.9, "reviewsCount": "348 đánh giá"}
    s_sold, r_sold, _ = score_product(sold, None)
    s_reviewed, _, _ = score_product(reviewed, None)
    # 5 sao không rõ bao nhiêu lượt không được thắng 4.9 sao từ 348 lượt đánh giá thật
    assert s_reviewed > s_sold
    assert not any("lượt" in r for r in r_sold)


# ---------------------------------------------------------------- 2. lọc phụ kiện bằng LLM
def test_accessory_search_still_goes_through_llm_filter(monkeypatch):
    seen = {}

    class FakeModel:
        async def ainvoke(self, messages):
            seen["prompt"] = messages[1].content
            return SimpleNamespace(
                content=json.dumps({"products": [{"id": "usb", "keep": False}, {"id": "pad", "keep": True}]})
            )

    monkeypatch.setattr(spec_fit, "get_chat_model", lambda **kw: FakeModel())
    items = [
        {"id": "usb", "name": "USB Bluetooth 5.0 - miếng lót chuột", "currentPrice": 45000},
        {"id": "pad", "name": "Tấm lót chuột gaming Havit", "currentPrice": 50000},
    ]
    crit = UniversalSearchCriteria(target_entity="lót chuột", is_accessory=True)
    kept = asyncio.run(spec_fit.screen(items, crit, "lót chuột"))
    assert [p["id"] for p in kept] == ["pad"]
    assert "CHỦ ĐÍCH tìm phụ kiện" in seen["prompt"]


# ---------------------------------------------------------------- 4. giữ lời đề nghị cuối câu trả lời
def test_history_keeps_the_offer_at_the_end_of_long_answers():
    sid = "test-offer-tail"
    session_memory._sessions.pop(sid, None)
    answer = (
        "Cả MSI Katana và Acer Nitro 5 đều tốt. " * 30 + "Bạn có muốn tôi kiểm tra các mẫu cụ thể trên các sàn không?"
    )
    session_memory.get_messages(sid).extend(
        [
            MessageItem(id="u", sender="user", text="katana hay nitro 5", timestamp="x"),
            MessageItem(id="a", sender="ai", text=answer, timestamp="x"),
        ]
    )
    history = session_memory.format_chat_history_for_prompt(sid, max_turns=2)
    assert "Bạn có muốn tôi kiểm tra các mẫu cụ thể" in history and len(history) < len(answer)
    session_memory._sessions.pop(sid, None)


# ---------------------------------------------------------------- 8. đổi chủ đề thì bỏ sản phẩm cũ
def test_new_topic_does_not_reuse_previous_products(monkeypatch):
    pads = [
        {
            "id": "fpt-1",
            "name": "Tấm lót chuột iCore IMP02",
            "platform": "fpt-shop",
            "platformName": "FPT Shop",
            "currentPrice": 59000,
            "originalPrice": 100000,
        }
    ]
    monkeypatch.setattr(session_memory, "get_last_products", lambda sid: pads)
    base = dict(session_id="s", user_query="mua quà sinh nhật cho bạn gái", intent="general_advice")

    new_topic = advisor_context.build_context(AgentState(**base, about_previous_products=False))
    assert "lót chuột" not in new_topic["products_context"] and new_topic["total_found"] == "0"

    follow_up = advisor_context.build_context(
        AgentState(**{**base, "user_query": "con này dùng bền không"}, about_previous_products=True)
    )
    assert "lót chuột" in follow_up["products_context"]


def test_router_reads_about_previous_products(monkeypatch):
    from core.agents import orchestrator as orch

    class FakeModel:
        async def ainvoke(self, messages):
            return SimpleNamespace(
                content=json.dumps(
                    {
                        "intent": "general_advice",
                        "about_previous_products": False,
                        "criteria": {
                            "category": "other",
                            "target_entity": "quà tặng",
                            "usage_purpose": "quà tặng sinh nhật",
                        },
                    }
                )
            )

    monkeypatch.setattr(orch, "get_chat_model", lambda **kw: FakeModel())
    state = asyncio.run(orch.OrchestratorAgent().route(AgentState(session_id="s2", user_query="mua quà cho bạn gái")))
    assert state.about_previous_products is False and state.intent == "general_advice"


def test_other_category_is_not_shown_to_the_advisor():
    text = advisor_context.format_criteria(
        UniversalSearchCriteria(category="other", category_name="Khác", max_price=1_000_000)
    )
    assert "Khác" not in text and "1,000,000" in text


def test_advisor_follows_router_scope_decision():
    """Câu hỏi mua sắm ngắn, mơ hồ ("nhiều tiền, nên mua con nào") không được Advisor tự từ chối là ngoài phạm vi."""
    in_scope = advisor_context.build_context(
        AgentState(session_id="s3", user_query="nên mua con nào", intent="general_advice")
    )
    out_scope = advisor_context.build_context(
        AgentState(session_id="s3", user_query="xem tử vi", intent="out_of_scope")
    )
    assert "KHÔNG áp dụng Trường hợp 4" in in_scope["scope_note"]
    assert "NGOÀI phạm vi" in out_scope["scope_note"]
