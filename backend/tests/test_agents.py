import pytest
from core.state import AgentState
from core.graph import ShopAIAgentWorkflow

@pytest.mark.anyio
async def test_orchestrator_and_advisor_flow():
    workflow = ShopAIAgentWorkflow()
    state = AgentState(
        session_id="test-session-1",
        user_query="Tìm giúp tôi laptop gaming giá 20 triệu"
    )
    
    result = await workflow.execute(state)
    
    assert result.intent == "search_products"
    assert len(result.found_products) > 0
    assert result.recommended_product is not None
    assert "ShopAI Copilot" in result.final_response

@pytest.mark.anyio
async def test_link_parser_intent():
    workflow = ShopAIAgentWorkflow()
    state = AgentState(
        session_id="test-session-2",
        user_query="Bóc tách link này giúp tôi https://shopee.vn/product/12345/6789"
    )
    
    result = await workflow.execute(state)
    
    assert result.intent == "parse_link"
    assert len(result.found_products) == 1
    assert result.found_products[0].platform == "shopee"
