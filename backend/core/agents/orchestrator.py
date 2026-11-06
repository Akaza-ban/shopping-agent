import json
import re
import logging
from typing import Dict, Any, Optional
from ..state import AgentState, UniversalSearchCriteria
from ..prompts.router_prompts import ROUTER_SYSTEM_PROMPT
from src.config import settings, get_chat_model

logger = logging.getLogger("orchestrator")

class OrchestratorAgent:
    """Agent phân loại ý định người dùng và trích xuất tiêu chí đa ngành hàng bằng LLM."""

    async def route(self, state: AgentState) -> AgentState:
        query = state.user_query.strip()
        
        # 1. Kiểm tra nhanh đường link URL bằng Regex
        url_match = re.search(r'https?://[^\s]+', query)
        if url_match:
            state.intent = "parse_link"
            state.target_link = url_match.group(0)
            return state

        # 2. Thử gọi LLM (DeepSeek qua OpenRouter hoặc Groq) để trích xuất tiêu chí có cấu trúc
        chat_model = get_chat_model(temperature=0.1)
        if chat_model:
            try:
                from langchain_core.messages import SystemMessage, HumanMessage
                messages = [
                    SystemMessage(content=ROUTER_SYSTEM_PROMPT),
                    HumanMessage(content=f"Yêu cầu của người dùng: {query}")
                ]
                
                # Gọi LLM (LangSmith Tracing sẽ tự động ghi lại nếu bật)
                response = await chat_model.ainvoke(messages)
                raw_text = response.content if hasattr(response, 'content') else str(response)

                # Làm sạch markdown nếu LLM bọc trong ```json ... ```
                json_text = raw_text
                if "```json" in json_text:
                    json_text = json_text.split("```json")[1].split("```")[0].strip()
                elif "```" in json_text:
                    json_text = json_text.split("```")[1].split("```")[0].strip()

                parsed_data = json.loads(json_text)
                
                # Gán Intent
                state.intent = parsed_data.get("intent", "search_products")
                
                # Gán Tiêu chí tìm kiếm đa ngành hàng
                criteria_data = parsed_data.get("criteria", {})
                if criteria_data:
                    state.criteria = UniversalSearchCriteria(**criteria_data)
                    logger.info(f"✨ [LLM Extracted] Intent: {state.intent} | Criteria: {state.criteria.model_dump()}")
                
                return state

            except Exception as e:
                logger.warning(f"⚠️ Lỗi khi gọi LLM bóc tách ({e}). Thử fallback sang Groq...")
                if settings.GROQ_API_KEY:
                    try:
                        from langchain_openai import ChatOpenAI
                        groq_fallback = ChatOpenAI(
                            base_url="https://api.groq.com/openai/v1",
                            api_key=settings.GROQ_API_KEY.strip(),
                            model=settings.GROQ_MODEL.strip() or "openai/gpt-oss-20b",
                            temperature=0.1,
                            max_tokens=1000
                        )
                        groq_resp = await groq_fallback.ainvoke(messages)
                        json_text = str(groq_resp.content).strip()
                        if "```json" in json_text:
                            json_text = json_text.split("```json")[1].split("```")[0].strip()
                        elif "```" in json_text:
                            json_text = json_text.split("```")[1].split("```")[0].strip()
                        parsed_data = json.loads(json_text)
                        state.intent = parsed_data.get("intent", "search_products")
                        criteria_data = parsed_data.get("criteria", {})
                        if criteria_data:
                            state.criteria = UniversalSearchCriteria(**criteria_data)
                            logger.info(f"✨ [Groq Fallback Extracted] Intent: {state.intent} | Criteria: {state.criteria.model_dump()}")
                        return state
                    except Exception as groq_err:
                        logger.warning(f"Fallback Groq thất bại: {groq_err}")

        # 3. Fallback Heuristics: Nếu không có kết nối LLM
        return self._fallback_route(state)

    def _fallback_route(self, state: AgentState) -> AgentState:
        """Cơ chế dự phòng bằng từ khóa khi chưa kết nối được LLM."""
        lower_query = state.user_query.lower()

        # Nhận diện intent
        if any(w in lower_query for w in ["so sánh", "khác nhau", "hơn"]):
            state.intent = "compare_products"
        elif any(w in lower_query for w in ["voucher", "giảm giá", "khuyến mãi", "deal", "mã"]):
            state.intent = "find_deal"
        else:
            state.intent = "search_products"

        # Trích xuất ngân sách cơ bản (ví dụ "30 triệu", "30tr")
        max_price = None
        price_match = re.search(r'(\d+)\s*(triệu|tr|củ)', lower_query)
        if price_match:
            max_price = float(price_match.group(1)) * 1_000_000

        # Phân loại danh mục cơ bản
        category = "all"
        if "laptop" in lower_query or "máy tính" in lower_query:
            category = "laptops"
        elif "điện thoại" in lower_query or "iphone" in lower_query or "samsung" in lower_query:
            category = "phones"
        elif "tai nghe" in lower_query or "loa" in lower_query:
            category = "audio"

        # Phân loại sàn cơ bản
        target_platforms = ["all"]
        if "tiki" in lower_query:
            target_platforms = ["tiki"]
        elif "lazada" in lower_query:
            target_platforms = ["lazada"]
        elif "shopee" in lower_query:
            target_platforms = ["shopee"]
        elif "tgdd" in lower_query or "thế giới di động" in lower_query:
            target_platforms = ["tgdd"]
        elif "dmx" in lower_query or "điện máy xanh" in lower_query:
            target_platforms = ["dmx"]

        state.criteria = UniversalSearchCriteria(
            category=category,
            max_price=max_price,
            target_platforms=target_platforms,
            cleaned_query=state.user_query
        )
        return state
