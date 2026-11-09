"""So sánh các sản phẩm giao diện đang giữ (VD sản phẩm đã lưu) bằng tool so sánh của agent, không qua khung chat."""

from typing import Any

from core.agents.comparison_agent import ComparisonAgent
from core.state import AgentState, ProductItemModel

comparison_agent = ComparisonAgent()


async def compare(products: list[dict[str, Any]], session_id: str | None = None) -> dict[str, Any]:
    state = AgentState(
        session_id=session_id or "compare",
        user_query="so sánh",
        found_products=[ProductItemModel(**p) for p in products],
    )
    state = await comparison_agent.compare(state)
    return {"summary": state.comparison_summary, "table": state.comparison_table}
