from ..state import AgentState
from ..tools.spec_comparator import SpecComparatorTool, mixed_categories, product_category
from services.catalog.category_resolver import category_resolver

class ComparisonAgent:
    """Agent chuyên so sánh giá cả, thông số kỹ thuật, bảo hành và đổi trả đa sàn."""

    def __init__(self):
        self.comparator = SpecComparatorTool()

    async def compare(self, state: AgentState) -> AgentState:
        if len(state.found_products) < 2:
            return state
        products_dict = [p.model_dump() for p in state.found_products]
        await category_resolver.resolve(products_dict)
        same_kind = None
        if not mixed_categories(products_dict):
            sources = {(category_resolver.source_of(p) or (None,))[0] for p in products_dict}
            if len(sources) > 1 or None in sources:
                same_kind = await category_resolver.same_kind(products_dict)
        comparison_res = await self.comparator.run(products=products_dict, same_kind=same_kind)

        state.comparison_summary = comparison_res.get("recommendation", "")
        state.comparison_table = comparison_res.get("table")
        state.comparison_markdown = comparison_res.get("markdown", "")
        if comparison_res.get("status") == "mixed_categories":
            state.search_notes.append(
                "Các sản phẩm KHÁC LOẠI (" + (", ".join(comparison_res.get("categories", [])) or "theo tên sản phẩm")
                + "): không lập bảng so sánh, "
                "không kết luận sản phẩm nào tốt hơn."
            )
        return state
