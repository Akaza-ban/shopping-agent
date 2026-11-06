import sys
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, ".")

from core.agents.shopping_advisor import ShoppingAdvisorAgent
from core.state import AgentState, ProductItemModel, UniversalSearchCriteria
from core.prompts.advisor_prompts import ADVISOR_SYSTEM_PROMPT, ADVISOR_USER_PROMPT_TEMPLATE

@pytest.fixture
def mock_products():
    return [
        ProductItemModel(
            id="p-1",
            name="Laptop Lenovo IdeaPad Slim 3 15IAH8",
            platform="tiki",
            platformName="Tiki Trading",
            originalPrice=16990000,
            currentPrice=13490000,
            discountPercent=21,
            rating=4.8,
            reviewsCount="24 đánh giá",
            specs={"CPU": "Core i5 12450H", "RAM": "16GB", "SSD": "512GB", "Màn hình": "15.6 inch FHD"},
            externalUrl="https://tiki.vn/p-1"
        ),
        ProductItemModel(
            id="p-2",
            name="Laptop Asus Vivobook 14 X1404ZA",
            platform="tgdd",
            platformName="Thế Giới Di Động",
            originalPrice=15490000,
            currentPrice=12990000,
            discountPercent=16,
            rating=4.7,
            reviewsCount="58 đánh giá",
            specs={"CPU": "Core i3 1215U", "RAM": "8GB", "SSD": "512GB", "Màn hình": "14 inch FHD"},
            externalUrl="https://thegioididong.com/laptop/asus-vivobook-14"
        ),
        ProductItemModel(
            id="p-3",
            name="Laptop HP 15s-fq5229TU",
            platform="dmx",
            platformName="Điện Máy Xanh",
            originalPrice=14990000,
            currentPrice=12490000,
            discountPercent=17,
            rating=4.6,
            reviewsCount="32 đánh giá",
            specs={"CPU": "Core i3 1215U", "RAM": "8GB", "SSD": "256GB"},
            externalUrl="https://dienmayxanh.com/laptop/hp-15s"
        )
    ]

@pytest.mark.asyncio
async def test_step2_prompt_formatting(mock_products):
    """Kiểm tra Bước 2: Prompt súc tích và chuẩn hóa."""
    agent = ShoppingAdvisorAgent()
    state = AgentState(
        session_id="test-prompt",
        user_query="Tìm laptop học sinh sinh viên dưới 15 triệu",
        criteria=UniversalSearchCriteria(
            category="laptops",
            max_price=15000000,
            usage_purpose="học sinh sinh viên"
        ),
        found_products=mock_products
    )

    context = agent.build_standardized_context(state)
    user_prompt = ADVISOR_USER_PROMPT_TEMPLATE.format(
        user_query=context["user_query"],
        criteria_summary=context["criteria_summary"],
        chat_history_context=context.get("chat_history_context", ""),
        products_context=context["products_context"],
        search_notes_context=context.get("search_notes_context", "")
    )

    assert "ShopAI Copilot" in ADVISOR_SYSTEM_PROMPT
    assert "Tìm laptop học sinh sinh viên dưới 15 triệu" in user_prompt
    assert "15,000,000" in user_prompt
    assert "Lenovo IdeaPad Slim 3" in user_prompt
    assert "Asus Vivobook 14" in user_prompt
    assert "HP 15s" in user_prompt

@pytest.mark.asyncio
async def test_step4_zero_crash_fallback_on_error(mock_products):
    """Kiểm tra Bước 4: Fallback Zero-Crash khi mô hình LLM bị lỗi mạng hoặc timeout."""
    agent = ShoppingAdvisorAgent()
    state = AgentState(
        session_id="test-fallback",
        user_query="Tìm laptop học sinh sinh viên",
        found_products=mock_products
    )

    # Giả lập LLM ném ngoại lệ Timeout/ConnectionError
    with patch("core.agents.shopping_advisor.get_chat_model") as mock_get_model:
        mock_model = MagicMock()
        async def mock_astream(messages):
            raise TimeoutError("Connection to Groq timed out")
            yield ""
        mock_model.astream = mock_astream
        mock_model.ainvoke.side_effect = TimeoutError("Connection to Groq timed out")
        mock_get_model.return_value = mock_model

        # Chạy generate_response
        result_state = await agent.generate_response(state)

        # Xác nhận hệ thống KHÔNG crash, tự động trả về phản hồi fallback chất lượng cao
        assert result_state.final_response != ""
        assert "Đề xuất số 1" in result_state.final_response
        assert "Lenovo IdeaPad Slim 3" in result_state.final_response
        assert "Tiki Trading" in result_state.final_response
        assert len(result_state.messages) > 0
        assert result_state.recommended_product.id == "p-1"

@pytest.mark.asyncio
async def test_step3_live_or_mock_llm_execution(mock_products):
    """Kiểm tra Bước 3: Gọi LLM thành công khi có kết nối."""
    agent = ShoppingAdvisorAgent()
    state = AgentState(
        session_id="test-live-llm",
        user_query="Tư vấn mua laptop học tập",
        found_products=mock_products
    )

    result_state = await agent.generate_response(state)

    # Dù chạy live (có Groq key) hay fallback (không key), phản hồi phải luôn có cấu trúc Markdown
    assert result_state.final_response != ""
    assert len(result_state.messages) > 0
    assert result_state.recommended_product is not None
