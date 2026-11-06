from typing import Dict, Any
from .state import AgentState, ProductItemModel
from .agents.orchestrator import OrchestratorAgent
from .agents.shopping_advisor import ShoppingAdvisorAgent
from .agents.comparison_agent import ComparisonAgent
from .agents.link_parser_agent import LinkParserAgent
from .agents.deal_finder_agent import DealFinderAgent
from .tools.ecom_search import EcomSearchTool

class ShopAIAgentWorkflow:
    """Workflow điều phối toàn bộ chu trình xử lý của các Agent."""

    def __init__(self):
        self.orchestrator = OrchestratorAgent()
        self.advisor = ShoppingAdvisorAgent()
        self.comparator = ComparisonAgent()
        self.link_parser = LinkParserAgent()
        self.deal_finder = DealFinderAgent()
        self.search_tool = EcomSearchTool()

    async def execute(self, state: AgentState) -> AgentState:
        # Bước 1: Router / Orchestrator phân loại ý định
        state = await self.orchestrator.route(state)

        # Bước 2: Kích hoạt Agent chuyên trách dựa theo intent
        if state.intent == "parse_link":
            state = await self.link_parser.parse(state)
        elif state.intent == "search_products" or state.intent == "compare_products":
            # Gọi công cụ tìm kiếm sàn kèm criteria đã bóc tách
            raw_products = await self.search_tool.run(
                query=state.user_query,
                category=state.criteria.category if state.criteria else "all",
                criteria=state.criteria,
                limit=4
            )
            state.found_products = [ProductItemModel(**p) for p in raw_products]
            
            if state.intent == "compare_products":
                state = await self.comparator.compare(state)
            
            state = await self.advisor.generate_response(state)
        elif state.intent == "find_deal":
            state = await self.deal_finder.find_deals(state)
        else:
            state = await self.advisor.generate_response(state)

        return state
