from ..state import AgentState
from ..tools.spec_comparator import SpecComparatorTool

class ComparisonAgent:
    """Agent chuyên so sánh giá cả và thông số kỹ thuật đa sàn."""

    def __init__(self):
        self.comparator = SpecComparatorTool()

    async def compare(self, state: AgentState) -> AgentState:
        products_dict = [p.model_dump() for p in state.found_products]
        comparison_res = await self.comparator.run(products=products_dict)
        
        state.comparison_summary = comparison_res.get("recommendation", "")
        return state
