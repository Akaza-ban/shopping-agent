import pytest

from core.graph import ShopAIAgentWorkflow
from core.state import AgentState
from database.connection import init_db


@pytest.mark.anyio
async def test_orchestrator_and_advisor_flow():
    await init_db()  # máy chạy CI không có shopai.db sẵn: tạo bảng như lúc máy chủ khởi động
    workflow = ShopAIAgentWorkflow()
    state = AgentState(session_id="test-session-1", user_query="Tìm giúp tôi laptop gaming giá 20 triệu")

    result = await workflow.execute(state)

    assert result.intent == "search_products"
    assert len(result.found_products) > 0
    assert result.recommended_product is not None
    # Câu trả lời đi thẳng vào nội dung (không chào / tự giới thiệu), có nhắc sản phẩm được đề xuất
    assert result.final_response.strip()
    top_words = [w for w in result.recommended_product.name.split() if len(w) > 2][:3]
    assert any(w.lower() in result.final_response.lower() for w in top_words)


@pytest.mark.anyio
async def test_link_parser_intent():
    workflow = ShopAIAgentWorkflow()
    state = AgentState(
        session_id="test-session-2", user_query="Bóc tách link này giúp tôi https://shopee.vn/product/12345/6789"
    )

    result = await workflow.execute(state)

    assert result.intent == "parse_link"
    assert result.found_products == []
    assert "chưa hỗ trợ đọc link Shopee" in result.final_response
