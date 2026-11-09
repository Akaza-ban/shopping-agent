"""Workflow của trợ lý mua sắm, dựng bằng LangGraph.

    START -> load_session -> route -> clarify ─┬─ ask / smalltalk ─────────────────────┐
                                               ├─ parse_link ──────────────┐           │
                                               ├─ search ─┐                │           │
                                               ├─ deal ───┴─> compare ─> respond ─> finalize -> END
                                               └─ respond ─────────────────┘

Mỗi node đọc / sửa AgentState và phát event SSE (core/events.py) qua stream writer.
Nghiệp vụ của từng bước nằm ở core/flows/ (hỏi làm rõ, tìm kiếm, gợi ý) và core/agents/.
"""

import logging
import time
from collections.abc import AsyncIterator
from typing import Any

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph

from memory.session_manager import session_memory

from . import events
from .agents.comparison_agent import ComparisonAgent
from .agents.deal_finder_agent import DealFinderAgent
from .agents.link_parser_agent import LinkParserAgent
from .agents.orchestrator import OrchestratorAgent
from .agents.shopping_advisor import ShoppingAdvisorAgent
from .constants import SEARCH_INTENTS
from .flows import clarification, suggestions
from .flows.search_flow import run_search
from .state import AgentState, MessageItem, ProductItemModel
from .tools.ecom_search import EcomSearchTool

logger = logging.getLogger("graph")


def _updates(state: AgentState) -> dict[str, Any]:
    """Node trả về toàn bộ các trường của state (agent con sửa state tại chỗ)."""
    return {name: getattr(state, name) for name in AgentState.model_fields}


class ShopAIAgentWorkflow:
    """Điều phối các agent theo graph ở trên, kèm trí nhớ hội thoại nhiều lượt."""

    def __init__(self):
        self.orchestrator = OrchestratorAgent()
        self.advisor = ShoppingAdvisorAgent()
        self.comparator = ComparisonAgent()
        self.link_parser = LinkParserAgent()
        self.deal_finder = DealFinderAgent()
        self.search_tool = EcomSearchTool()
        self.graph = self._build_graph()

    # API công khai
    async def execute(self, state: AgentState) -> AgentState:
        """Chạy trọn một lượt, trả về state cuối."""
        result = await self.graph.ainvoke(state)
        return AgentState(**result) if isinstance(result, dict) else result

    async def execute_stream(self, state: AgentState) -> AsyncIterator[dict[str, Any]]:
        """Chạy một lượt, phát dần các event SSE."""
        async for event in self.graph.astream(state, stream_mode="custom"):
            yield event

    # Dựng graph
    def _build_graph(self):
        g = StateGraph(AgentState)
        g.add_node("load_session", self._node_load_session)
        g.add_node("route", self._node_route)
        g.add_node("clarify", self._node_clarify)
        g.add_node("ask", self._node_ask)
        g.add_node("smalltalk", self._node_ask)
        g.add_node("parse_link", self._node_parse_link)
        g.add_node("search", self._node_search)
        g.add_node("deal", self._node_deal)
        g.add_node("compare", self._node_compare)
        g.add_node("respond", self._node_respond)
        g.add_node("finalize", self._node_finalize)

        g.add_edge(START, "load_session")
        g.add_edge("load_session", "route")
        g.add_edge("route", "clarify")
        g.add_conditional_edges(
            "clarify",
            self._next_after_clarify,
            {
                "ask": "ask",
                "smalltalk": "smalltalk",
                "parse_link": "parse_link",
                "search": "search",
                "deal": "deal",
                "respond": "respond",
            },
        )
        g.add_edge("ask", "finalize")
        g.add_edge("smalltalk", "finalize")
        g.add_edge("parse_link", "respond")
        g.add_edge("search", "compare")
        g.add_edge("deal", "compare")
        g.add_edge("compare", "respond")
        g.add_edge("respond", "finalize")
        g.add_edge("finalize", END)
        return g.compile(name="shopai_agent")

    @staticmethod
    def _next_after_clarify(state: AgentState) -> str:
        if state.clarification:
            return "ask"
        if state.intent == "smalltalk":
            return "smalltalk"
        if state.intent == "parse_link":
            return "parse_link"
        if state.intent in SEARCH_INTENTS:
            return "search"
        if state.intent == "find_deal":
            return "deal"
        return "respond"

    # Các node
    async def _node_load_session(self, state: AgentState) -> dict[str, Any]:
        if state.session_id:
            await session_memory.load_session_from_db(state.session_id)
        return {}

    async def _node_route(self, state: AgentState) -> dict[str, Any]:
        """Hiểu câu hỏi: ý định + tiêu chí tìm kiếm; sàn chọn trên giao diện ghi đè sàn trong câu hỏi."""
        state = await self.orchestrator.route(state)
        if state.intent != "smalltalk":
            get_stream_writer()(events.status("routing", "Đã hiểu yêu cầu, đang xử lý..."))
        platform = (state.platform_filter or "").lower().strip()
        if platform and platform != "all" and state.criteria:
            state.criteria = state.criteria.model_copy(update={"target_platforms": [platform]})
        return _updates(state)

    async def _node_clarify(self, state: AgentState) -> dict[str, Any]:
        if state.intent == "smalltalk":
            return {}  # giữ nguyên câu hỏi làm rõ đang chờ (nếu có)
        clarification.apply_pending(state)
        clarification.maybe_ask(state)
        return _updates(state)

    async def _node_ask(self, state: AgentState) -> dict[str, Any]:
        """Trả lời ngay không cần tìm: câu hỏi làm rõ, hoặc câu chào hỏi / nói chuyện phiếm."""
        writer = get_stream_writer()
        if state.clarification:
            writer(events.clarification(state.clarification))
        writer(events.token(state.final_response))
        return {}

    async def _node_parse_link(self, state: AgentState) -> dict[str, Any]:
        writer = get_stream_writer()
        writer(events.status("parsing_link", "Đang bóc tách thông tin và thẩm định liên kết sản phẩm..."))
        state = await self.link_parser.parse(state)
        if state.found_products:
            writer(events.products(state.found_products))
        return _updates(state)

    async def _node_search(self, state: AgentState) -> dict[str, Any]:
        writer = get_stream_writer()
        async for event in run_search(self.search_tool, state):
            writer(event)
        if state.found_products:
            writer(events.products(state.found_products))
        return _updates(state)

    async def _node_deal(self, state: AgentState) -> dict[str, Any]:
        """Săn deal: cho sản phẩm vừa xem ở lượt trước (nếu câu hỏi không nêu sản phẩm mới), hoặc tìm mới."""
        writer = get_stream_writer()
        writer(events.status("finding_deal", "Đang săn các deal và mức giảm giá tốt nhất..."))
        c = state.criteria
        has_target = bool(c and (c.target_entity or c.product_type))
        last_products = session_memory.get_last_products(state.session_id) if state.session_id else []
        if not has_target and last_products and state.about_previous_products is not False:
            state.found_products = [ProductItemModel(**p) for p in last_products]
        elif c:
            async for event in run_search(self.search_tool, state):
                writer(event)
        state = await self.deal_finder.find_deals(state)
        if state.found_products:
            writer(events.products(state.found_products))
        return _updates(state)

    async def _node_compare(self, state: AgentState) -> dict[str, Any]:
        if len(state.found_products) < 2:
            return {}
        writer = get_stream_writer()
        writer(events.status("comparing", "Đang tổng hợp bảng so sánh cấu hình, giá, bảo hành và đổi trả..."))
        state = await self.comparator.compare(state)
        if state.comparison_table:
            writer(events.comparison(state.comparison_summary, state.comparison_table))
        return _updates(state)

    async def _node_respond(self, state: AgentState) -> dict[str, Any]:
        writer = get_stream_writer()
        if state.intent == "parse_link" and not state.found_products and state.final_response:
            writer(events.token(state.final_response))
            return {}
        writer(
            events.status(
                "synthesizing",
                "Chuyên gia AI đang phân tích ưu nhược điểm và soạn lời khuyên..."
                if state.found_products
                else "Đang soạn câu trả lời...",
            )
        )
        async for token in self.advisor.generate_response_stream(state):
            writer(events.token(token))
        return _updates(state)

    async def _node_finalize(self, state: AgentState) -> dict[str, Any]:
        """Lưu lượt hội thoại (RAM + SQLite), phát câu hỏi gợi ý và event kết thúc."""
        if state.session_id and state.final_response:
            now_ms = int(time.time() * 1000)
            session_memory.save_turn(
                session_id=state.session_id,
                user_message=MessageItem(
                    id=f"msg-user-{now_ms}", sender="user", text=state.user_query, timestamp="Vừa xong"
                ),
                ai_message=MessageItem(
                    id=f"msg-ai-{now_ms + 1}", sender="ai", text=state.final_response, timestamp="Vừa xong"
                ),
                products=state.found_products,
                criteria=state.criteria,
            )

        state.suggested_questions = suggestions.generate(state)
        writer = get_stream_writer()
        writer(events.suggestions(state.suggested_questions))
        writer(
            events.done(
                {
                    "session_id": state.session_id,
                    "intent": state.intent,
                    "recommended_product": state.recommended_product.model_dump()
                    if state.recommended_product
                    else None,
                    "clarification": state.clarification,
                    "relaxed_search": state.relaxed_search,
                    "search_notes": state.search_notes,
                }
            )
        )
        return {"suggested_questions": state.suggested_questions}
