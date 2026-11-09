"""Tìm sản phẩm theo tiêu chí của người dùng, có 2 phương án dự phòng:

1. Nới lỏng: không có sản phẩm khớp hoàn toàn -> lần lượt bỏ thông số chi tiết, nới ngân sách +20%, mở rộng sang hãng khác.
2. Upsell:  có sản phẩm trong ngân sách nhưng chưa cái nào xác nhận đúng thông số bắt buộc (VD GPU)
            -> tìm thêm sản phẩm ĐÚNG thông số nhưng vượt ngân sách (tới +20%), ghi chú cho Advisor.

run_search() là async generator: phát các event status / products trong lúc tìm, ghi kết quả vào state.found_products.
"""

import logging
import re
from collections.abc import AsyncIterator
from typing import Any

from services.catalog.ranker import rank_products, verifiable_attributes
from shared.types import RawProduct

from .. import events
from ..constants import BUDGET_ROUND_TO, BUDGET_WIDEN_FACTOR, RESULT_LIMIT
from ..state import AgentState, ProductItemModel, UniversalSearchCriteria
from ..tools.ecom_search import EcomSearchTool

logger = logging.getLogger("search_flow")

RELAXABLE_INTENTS = ("search_products", "find_deal")


def widened_budget(max_price: float) -> float:
    """Ngân sách nới thêm 20%, làm tròn tới 100.000 đ."""
    return float(round(max_price * BUDGET_WIDEN_FACTOR / BUDGET_ROUND_TO) * BUDGET_ROUND_TO)


def _strip_terms(text: str, terms: list[str]) -> str:
    for t in terms:
        if t:
            text = re.sub(re.escape(t), " ", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()


def relaxation_steps(criteria: UniversalSearchCriteria) -> list[tuple[UniversalSearchCriteria, str]]:
    """Các bước nới lỏng tiêu chí (cộng dồn), mỗi bước kèm mô tả đã nới gì.

    Thứ tự: bỏ thông số chi tiết -> nới ngân sách -> mở rộng sang hãng khác.
    """
    steps: list[tuple[UniversalSearchCriteria, str]] = []
    current = criteria
    changes: list[str] = []
    base_query = criteria.cleaned_query or criteria.product_type or criteria.target_entity or ""

    attr_values = [
        str(v).strip() for v in (criteria.attributes or {}).values() if isinstance(v, str) and str(v).strip()
    ]
    if criteria.attributes:
        changes.append(f"bỏ yêu cầu {', '.join(attr_values)}" if attr_values else "bỏ yêu cầu thông số chi tiết")
        base_query = _strip_terms(base_query, attr_values)
        current = current.model_copy(update={"attributes": {}, "cleaned_query": base_query})
        steps.append((current, "; ".join(changes)))

    if criteria.max_price:
        widened = widened_budget(criteria.max_price)
        changes.append(f"nới ngân sách lên {widened:,.0f} đ")
        current = current.model_copy(update={"max_price": widened})
        steps.append((current, "; ".join(changes)))

    if criteria.brands:
        changes.append("mở rộng sang các hãng khác")
        base_query = _strip_terms(base_query, list(criteria.brands))
        current = current.model_copy(update={"brands": [], "cleaned_query": base_query})
        steps.append((current, "; ".join(changes)))

    fallback_query = criteria.target_entity or criteria.product_type or ""
    return [
        (c if c.cleaned_query.strip() else c.model_copy(update={"cleaned_query": fallback_query}), desc)
        for c, desc in steps
    ]


def _fully_verified(product: dict[str, Any]) -> bool:
    status = product.get("attributeMatch") or {}
    return bool(status) and all(v == "verified" for v in status.values())


def _needs_upsell(criteria: UniversalSearchCriteria, products: list[RawProduct]) -> bool:
    """Có thông số bắt buộc và ngân sách, nhưng chưa sản phẩm nào xác nhận đúng thông số."""
    return bool(
        verifiable_attributes(criteria) and criteria.max_price and not any(_fully_verified(p) for p in products)
    )


async def _search(
    tool: EcomSearchTool, query: str, criteria, notes: list[str], force_refresh: bool = False
) -> list[RawProduct]:
    return await tool.run(
        query=query,
        category=criteria.category if criteria else "all",
        criteria=criteria,
        limit=RESULT_LIMIT,
        force_refresh=force_refresh,
        notes=notes,
    )


async def _upsell(
    tool: EcomSearchTool, state: AgentState, search_query: str, products: list[RawProduct], widened: float, wanted: str
) -> list[RawProduct]:
    """Thêm sản phẩm ĐÚNG thông số nhưng vượt ngân sách (tới widened) vào danh sách, ghi chú cho Advisor."""
    criteria = state.criteria
    alt = await _search(tool, search_query, criteria.model_copy(update={"max_price": widened}), [], force_refresh=True)
    known_ids = {p.get("id") for p in products}
    alt_ok = [p for p in alt if _fully_verified(p) and p.get("id") not in known_ids]
    if not alt_ok:
        state.search_notes.append(
            f"Đã tìm thêm tới {widened:,.0f} đ nhưng vẫn không có sản phẩm nào xác nhận đúng {wanted} trên các sàn đã quét."
        )
        return products
    ranked, _ = rank_products(products + alt_ok, criteria)
    state.search_notes.append(
        f"Trong ngân sách không có sản phẩm đúng {wanted}; khi tìm thêm tới {widened:,.0f} đ có "
        f"{len(alt_ok)} sản phẩm ĐÚNG yêu cầu nhưng vượt ngân sách (đã đưa vào danh sách, lý do ghi 'Vượt ngân sách')."
    )
    return ranked[:RESULT_LIMIT]


async def run_search(tool: EcomSearchTool, state: AgentState) -> AsyncIterator[events.Event]:
    """Tìm theo state.criteria (không có thì theo câu hỏi gốc); kết quả ghi vào state.found_products."""
    criteria = state.criteria
    search_query = criteria.cleaned_query if (criteria and criteria.cleaned_query) else state.user_query
    can_relax = criteria is not None and state.intent in RELAXABLE_INTENTS
    yield events.status("retrieval", f"Đang truy xuất kho dữ liệu & quét các sàn cho '{search_query}'...")
    raw_products = await _search(tool, search_query, criteria, state.search_notes)

    if not raw_products and can_relax:
        for relaxed, description in relaxation_steps(criteria):
            yield events.status(
                "relaxing", f"Không có sản phẩm khớp hoàn toàn yêu cầu, đang tìm phương án gần nhất ({description})..."
            )
            relaxed_notes: list[str] = []
            raw_products = await _search(tool, relaxed.cleaned_query, relaxed, relaxed_notes)
            if raw_products:
                state.relaxed_search = description
                state.search_notes.extend(relaxed_notes)
                logger.info(f"[Relaxed Search] '{search_query}' -> {description}: {len(raw_products)} sản phẩm")
                break

    if raw_products and can_relax and _needs_upsell(criteria, raw_products):
        widened = widened_budget(criteria.max_price)
        wanted = ", ".join(verifiable_attributes(criteria).values())
        yield events.products([ProductItemModel(**p) for p in raw_products])
        yield events.status(
            "upsell", f"Chưa có sản phẩm đúng {wanted} trong ngân sách, đang tìm thêm tới {widened:,.0f} đ..."
        )
        raw_products = await _upsell(tool, state, search_query, raw_products, widened, wanted)

    state.found_products = [ProductItemModel(**p) for p in raw_products]
