from ..state import AgentState, ProductItemModel


class DealFinderAgent:
    """Agent săn deal: đưa các sản phẩm đang giảm giá sâu nhất lên đầu và ghi chú ưu đãi thực tế để Advisor trình bày."""

    @staticmethod
    def _saving(p: ProductItemModel) -> float:
        return max(0.0, p.originalPrice - p.currentPrice)

    async def find_deals(self, state: AgentState) -> AgentState:
        products = state.found_products
        if not products:
            return state

        discounted = sorted(
            (p for p in products if p.discountPercent > 0 and self._saving(p) > 0),
            key=lambda p: (p.discountPercent, self._saving(p)),
            reverse=True,
        )
        if not discounted:
            state.search_notes.append(
                "Không sản phẩm nào trong kết quả đang giảm so với giá niêm yết của sàn; "
                "chỉ nêu giá hiện tại, không hứa hẹn voucher hay flash sale."
            )
            return state

        deal_ids = {p.id for p in discounted}
        state.found_products = discounted + [p for p in products if p.id not in deal_ids]
        lines = [
            f"{p.name} tại {p.platformName}: giảm {p.discountPercent}% "
            f"({p.originalPrice:,.0f} đ -> {p.currentPrice:,.0f} đ, tiết kiệm {self._saving(p):,.0f} đ)"
            for p in discounted[:3]
        ]
        state.search_notes.append(
            "Ưu đãi đang có (đã xếp theo mức giảm; giá niêm yết do sàn công bố, chưa gồm voucher riêng của người dùng):\n"
            + "\n".join(lines)
        )
        return state
