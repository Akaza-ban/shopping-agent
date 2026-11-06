"""So sánh các sản phẩm giao diện đang giữ (VD sản phẩm đã lưu) bằng tool so sánh của agent, không qua khung chat."""
from typing import Any, Dict, List, Optional

from core.agents.comparison_agent import ComparisonAgent
from core.state import AgentState, ProductItemModel

comparison_agent = ComparisonAgent()


async def compare(products: List[Dict[str, Any]], session_id: Optional[str] = None) -> Dict[str, Any]:
    state = AgentState(session_id=session_id or "compare", user_query="so sánh",
                       found_products=[ProductItemModel(**p) for p in products])
    state = await comparison_agent.compare(state)
    return {"summary": state.comparison_summary, "table": state.comparison_table}
