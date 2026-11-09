"""Tool tìm sản phẩm thật trên các sàn: cache -> kho RAG -> cào trực tiếp, rồi làm sạch, kiểm định giá, xếp hạng.

    run()
     ├─ from_cache()   có kết quả -> trả luôn
     ├─ bắt đầu _crawl() ở nền ┐
     ├─ from_rag()     có -> hủy cào, trả luôn
     └─ from_crawl()  <────────┘ -> remember()

Các nguồn kết quả: search_sources.py. Đối chiếu thông số: attribute_match.py.
"""

import asyncio
import logging
import re
from collections.abc import Iterable

from database.repositories import product_repository
from integrations.platforms import PlatformAdapter, all_platforms, display_names, resolve_targets
from integrations.platforms.errors import crawling
from services.catalog.category_resolver import category_resolver, with_noun
from services.catalog.data_processor import data_processor
from services.catalog.enricher import product_enricher
from services.catalog.ranker import rank_products
from services.pricing import guardrails as price_guardrails
from shared.exceptions import CrawlerError
from shared.types import RawProduct

from ..state import UniversalSearchCriteria
from . import attribute_match, search_sources
from .base import BaseTool
from .search_sources import SearchRequest

logger = logging.getLogger("ecom_search")

# Cụm chỉ giá trong câu hỏi ("dưới 20 triệu", "tầm 5tr") - bỏ khỏi từ khóa gửi cho sàn
PRICE_PHRASE_RE = re.compile(
    r"(?:\b(?:dưới|trên|từ|khoảng|tầm|giá|tối đa|không quá)\s+)?"
    r"\d+(?:[.,]\d+)?\s*(?:-|–|đến|tới)?\s*\d*(?:[.,]\d+)?\s*(?:triệu|tr|củ|k|nghìn|ngàn)\b",
    re.IGNORECASE,
)

DETAIL_BUDGET_SECONDS = 2.0  # thời gian tối đa chờ đọc trang chi tiết trong một lượt
CATEGORY_BUDGET_SECONDS = 6.0  # thời gian tối đa chờ LLM quy đổi danh mục mới


def _interleave(per_platform: Iterable[list[RawProduct]], cap: int) -> list[RawProduct]:
    """Đan xen kết quả các sàn (1 của sàn A, 1 của sàn B...) để so sánh giá công bằng; tối đa `cap` sản phẩm."""
    per_platform = [items for items in per_platform if items]
    out: list[RawProduct] = []
    for i in range(max((len(items) for items in per_platform), default=0)):
        out += [items[i] for items in per_platform if i < len(items)]
    return out[:cap]


class EcomSearchTool(BaseTool):
    name = "ecom_search"
    description = f"Tìm kiếm sản phẩm thực tế từ các sàn và hệ thống bán lẻ ({display_names()})"

    def __init__(self, platforms: list[PlatformAdapter] | None = None):
        self.platforms = platforms if platforms is not None else all_platforms()

    async def run(
        self,
        query: str,
        category: str = "all",
        criteria: UniversalSearchCriteria | None = None,
        platform: str = "all",
        limit: int = 6,
        force_refresh: bool = False,
        notes: list[str] | None = None,
    ) -> list[RawProduct]:
        """Tìm sản phẩm; `notes` nhận các ghi chú độ tin cậy cho Advisor; force_refresh bỏ qua cache và kho RAG."""
        search = self._prepare(query, category, criteria, platform, limit, notes)
        if search is None:
            return []

        if not force_refresh:
            cached = await search_sources.from_cache(self, search)
            if cached:
                return cached

        crawl_notes: list[str] = []
        crawl = asyncio.create_task(self._crawl(search.keyword, criteria, platform, limit, crawl_notes))
        if not force_refresh:
            stored = await search_sources.from_rag(self, search)
            if stored:
                crawl.cancel()
                return stored

        products = await search_sources.from_crawl(self, search, crawl, crawl_notes)
        await search_sources.remember(search, products)
        return products

    @staticmethod
    def _prepare(query, category, criteria, platform, limit, notes) -> SearchRequest | None:
        """Từ khóa thực sự tìm và sàn mục tiêu (sàn chọn trên giao diện, hoặc sàn router trích từ câu hỏi)."""
        keyword = criteria.cleaned_query if (criteria and criteria.cleaned_query) else query
        if not keyword.strip():
            return None
        target = platform.lower().strip() if (platform and platform != "all") else "all"
        if target == "all" and criteria and criteria.target_platforms:
            target = criteria.target_platforms[0].lower().strip()
        return SearchRequest(
            keyword=keyword,
            criteria=criteria,
            category=category,
            target_platform=target,
            limit=limit,
            notes=notes if notes is not None else [],
        )

    @staticmethod
    def optimize_crawler_query(query: str, criteria: UniversalSearchCriteria | None) -> str:
        """Từ khóa gửi cho sàn: bỏ cụm chỉ giá, thêm tên loại sản phẩm nếu thiếu (trừ khi tìm phụ kiện)."""
        q = (criteria.cleaned_query if (criteria and criteria.cleaned_query) else query).strip()
        q = re.sub(PRICE_PHRASE_RE, " ", q)
        q = re.sub(r"\s+", " ", q).strip() or query.strip()
        if criteria and criteria.is_accessory:
            return q
        if criteria and criteria.target_entity:
            entity = criteria.target_entity.strip().lower()
            if entity and entity not in q.lower():
                return f"{entity} {q}"
        return q

    async def _finalize(
        self,
        products: list[RawProduct],
        criteria: UniversalSearchCriteria | None,
        notes: list[str],
        limit: int,
        detail_budget: float = DETAIL_BUDGET_SECONDS,
    ) -> list[RawProduct]:
        """Bước chung cho mọi nguồn: đọc trang chi tiết, loại giá bất thường, đối chiếu thông số, xếp hạng, cắt `limit`."""
        if not products:
            return products
        products = await product_enricher.enrich(products, max_items=max(limit * 2, 8), budget_seconds=detail_budget)
        references = await product_repository.get_reference_prices([p.get("name", "") for p in products])
        products, rejected = price_guardrails.screen_products(products, references)
        if rejected:
            notes.append(
                f"Đã loại {len(rejected)} sản phẩm có giá bất thường (nghi đọc nhầm giá trả góp, phụ kiện hoặc lỗi trang)."
            )
        products = attribute_match.annotate(products, criteria, notes)
        if criteria:
            products, rank_notes = rank_products(products, criteria)
            notes.extend(rank_notes)
        freshness = attribute_match.freshness_note(products[:limit])
        if freshness and freshness not in notes:
            notes.append(freshness)
        return products[:limit]

    # Cào trực tiếp
    async def _crawl(
        self,
        search_keyword: str,
        criteria: UniversalSearchCriteria | None,
        platform: str,
        limit: int,
        notes: list[str],
    ) -> tuple[list[RawProduct], dict[str, int]]:
        """Cào song song các sàn và làm sạch dữ liệu; trả về (sản phẩm, số sản phẩm theo sàn)."""
        targets = self._target_platforms(platform, criteria, notes)
        crawler_query = self.optimize_crawler_query(search_keyword, criteria)
        if crawler_query != search_keyword:
            logger.info(f"[Layer 1 Universal] Query gốc: '{search_keyword}' -> Query crawler: '{crawler_query}'")

        cap = max(limit * 3, 12)
        per_platform = await self._search_platforms(targets, crawler_query, criteria, cap, notes, search_keyword)
        await self._apply_categories(per_platform, criteria)

        source_counts = {pid: len(items) for pid, items in per_platform.items()}
        return data_processor.process_product_list(_interleave(per_platform.values(), cap)), source_counts

    def _target_platforms(
        self, platform: str, criteria: UniversalSearchCriteria | None, notes: list[str]
    ) -> list[PlatformAdapter]:
        """Sàn cần tìm: sàn chọn trên giao diện / router trích từ câu hỏi; sàn không hỗ trợ thì tìm mọi sàn."""
        wanted = (
            [platform]
            if (platform and platform != "all")
            else ((criteria.target_platforms or ["all"]) if criteria else ["all"])
        )
        target_ids = {p.id for p in resolve_targets(wanted)}
        targets = [p for p in self.platforms if p.id in target_ids]
        if targets:
            return targets
        notes.append(f"Hệ thống không tìm trên sàn này; kết quả lấy từ {display_names()}.")
        return list(self.platforms)

    @staticmethod
    async def _search_platforms(targets, query, criteria, cap, notes, user_query) -> dict[str, list[RawProduct]]:
        """Gọi song song các sàn; sàn lỗi trả về danh sách rỗng, không làm hỏng cả lượt."""

        async def search_one(p: PlatformAdapter) -> list[RawProduct]:
            with crawling(p.name):
                return await p.search(query, criteria, cap, notes, user_query=user_query)

        results = await asyncio.gather(*(search_one(p) for p in targets), return_exceptions=True)
        per_platform: dict[str, list[RawProduct]] = {}
        for p, res in zip(targets, results, strict=True):
            if isinstance(res, CrawlerError):
                logger.warning(f"Lỗi khi tìm kiếm: {res}")
            elif isinstance(res, Exception):  # lỗi lập trình: ghi đủ traceback, các sàn khác vẫn chạy tiếp
                logger.error(f"[{p.name}] Lỗi không mong đợi khi tìm kiếm", exc_info=res)
            per_platform[p.id] = res if isinstance(res, list) else []
        return per_platform

    async def _apply_categories(
        self, per_platform: dict[str, list[RawProduct]], criteria: UniversalSearchCriteria | None
    ) -> None:
        """Gán ngành hàng theo danh mục của sàn (CategoryResolver) và bỏ phụ kiện khi người dùng không tìm phụ kiện."""
        items = [p for lst in per_platform.values() for p in lst]
        if not items:
            return
        task = asyncio.create_task(category_resolver.resolve(items))
        try:
            await asyncio.wait_for(asyncio.shield(task), CATEGORY_BUDGET_SECONDS)
        except TimeoutError:
            search_sources.keep_in_background(task)
            logger.info("Quy đổi danh mục mới chưa xong, tiếp tục ở nền; sản phẩm lượt này giữ ngành hàng tạm")
        wants_accessory = bool(criteria and criteria.is_accessory)
        for pid, lst in per_platform.items():
            kept = []
            for p in lst:
                mapping = category_resolver.lookup(p)
                if mapping is None:
                    kept.append(p)  # chưa rõ: để bộ lọc ngữ nghĩa phía sau quyết định
                    continue
                if mapping.is_accessory and not wants_accessory:
                    continue
                kept.append({**p, "category": mapping.category, "name": with_noun(p.get("name", ""), mapping.noun)})
            per_platform[pid] = kept
