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
from services.catalog import spec_fit
from services.catalog.category_resolver import category_resolver, with_noun
from services.catalog.data_processor import data_processor
from services.catalog.enricher import product_enricher
from services.catalog.ranker import rank_products, verifiable_attributes
from services.pricing import guardrails as price_guardrails
from shared.exceptions import CrawlerError
from shared.types import RawProduct

from ..state import UniversalSearchCriteria
from . import attribute_match, search_sources
from .base import BaseTool
from .search_sources import DETAIL_BUDGET_SECONDS, SearchRequest

logger = logging.getLogger("ecom_search")

# Cụm chỉ giá trong câu hỏi ("dưới 20 triệu", "tầm 5tr") - bỏ khỏi từ khóa gửi cho sàn
PRICE_PHRASE_RE = re.compile(
    r"(?:\b(?:dưới|trên|từ|khoảng|tầm|giá|tối đa|không quá)\s+)?"
    r"\d+(?:[.,]\d+)?\s*(?:-|–|đến|tới)?\s*\d*(?:[.,]\d+)?\s*(?:triệu|tr|củ|k|nghìn|ngàn)\b",
    re.IGNORECASE,
)

CATEGORY_BUDGET_SECONDS = 6.0  # thời gian tối đa chờ LLM quy đổi danh mục mới
CRAWL_BUDGET_SECONDS = 5.0  # chờ các sàn tối đa bấy nhiêu giây (nếu đã có sàn trả kết quả); sàn chậm chạy tiếp ở nền


def _interleave(per_platform: Iterable[list[RawProduct]], cap: int) -> list[RawProduct]:
    """Đan xen kết quả các sàn (1 của sàn A, 1 của sàn B...) để so sánh giá công bằng; tối đa `cap` sản phẩm."""
    per_platform = [items for items in per_platform if items]
    out: list[RawProduct] = []
    for i in range(max((len(items) for items in per_platform), default=0)):
        out += [items[i] for items in per_platform if i < len(items)]
    return out[:cap]


def _has_items(task: asyncio.Task) -> bool:
    return not task.cancelled() and task.exception() is None and bool(task.result())


async def _wait_for_results(tasks: list[asyncio.Task], budget: float) -> None:
    """Chờ mọi sàn tối đa `budget` giây; hết giờ mà chưa sàn nào có kết quả thì chờ tiếp tới khi có (hoặc hết sàn)."""
    done, pending = await asyncio.wait(tasks, timeout=budget)
    while pending and not any(_has_items(t) for t in done):
        more, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        done |= more


def _platform_result(p: PlatformAdapter, task: asyncio.Task) -> list[RawProduct]:
    """Kết quả của một sàn đã chạy xong; lỗi thì ghi log và trả danh sách rỗng."""
    if task.cancelled():
        return []
    error = task.exception()
    if isinstance(error, CrawlerError):
        logger.warning(f"Lỗi khi tìm kiếm: {error}")
    elif error is not None:  # lỗi lập trình: ghi đủ traceback, các sàn khác vẫn chạy tiếp
        logger.error(f"[{p.name}] Lỗi không mong đợi khi tìm kiếm", exc_info=error)
    return [] if error is not None else (task.result() or [])


async def _store_late_results(late: list[PlatformAdapter], tasks: dict[str, asyncio.Task]) -> None:
    """Chờ các sàn chậm xong (ở nền) rồi nạp kết quả vào kho RAG: lần hỏi sau có sẵn, khỏi cào lại."""
    await asyncio.wait([tasks[p.id] for p in late])
    items = [item for p in late for item in _platform_result(p, tasks[p.id])]
    if items:
        await search_sources.store_in_rag(data_processor.process_product_list(items))


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
        screened: bool = False,
    ) -> list[RawProduct]:
        """Bước chung cho mọi nguồn: đọc trang chi tiết, loại giá bất thường, đối chiếu thông số, xếp hạng, cắt `limit`.

        `screened`: nguồn đã đọc trang chi tiết và chấm mức hợp nhu cầu trong lúc lọc (search_sources.screen)
        -> không làm lại hai việc đó.
        """
        if not products:
            return products
        if not screened:
            products = await product_enricher.enrich(
                products, max_items=max(limit * 2, 8), budget_seconds=detail_budget
            )
        references = await product_repository.get_reference_prices([p.get("name", "") for p in products])
        products, rejected = price_guardrails.screen_products(products, references)
        if rejected:
            notes.append(
                f"Đã loại {len(rejected)} sản phẩm có giá bất thường (nghi đọc nhầm giá trả góp, phụ kiện hoặc lỗi trang)."
            )
        products = attribute_match.annotate(products, criteria, notes)
        if criteria:
            if not screened:
                # Đường cache (đã lọc từ lượt trước): chỉ chấm mức hợp nhu cầu; RAG / cào đã chấm trong screen()
                products = await spec_fit.assess(products, criteria, verifiable_attributes(criteria))
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
    async def _search_platforms(
        targets, query, criteria, cap, notes, user_query, budget: float = CRAWL_BUDGET_SECONDS
    ) -> dict[str, list[RawProduct]]:
        """Gọi song song các sàn; sàn lỗi trả về danh sách rỗng, không làm hỏng cả lượt.

        Hết `budget` giây mà đã có sàn trả kết quả thì đi tiếp với các sàn đã xong (một sàn chậm không kéo cả lượt
        chờ theo); sàn chậm chạy tiếp ở nền và nạp kết quả vào kho RAG cho lần hỏi sau.
        """
        platform_notes: dict[str, list[str]] = {p.id: [] for p in targets}

        async def search_one(p: PlatformAdapter) -> list[RawProduct]:
            with crawling(p.name):
                return await p.search(query, criteria, cap, platform_notes[p.id], user_query=user_query)

        tasks = {p.id: asyncio.create_task(search_one(p)) for p in targets}
        try:
            await _wait_for_results(list(tasks.values()), budget)
        except asyncio.CancelledError:  # đã có kết quả từ kho RAG: bỏ việc cào
            for task in tasks.values():
                task.cancel()
            raise

        per_platform: dict[str, list[RawProduct]] = {}
        late = [p for p in targets if not tasks[p.id].done()]
        for p in targets:
            if tasks[p.id].done():
                per_platform[p.id] = _platform_result(p, tasks[p.id])
                notes.extend(platform_notes[p.id])
        if late:
            names = ", ".join(p.name for p in late)
            notes.append(f"{names} phản hồi chậm nên chưa có trong kết quả lượt này.")
            logger.info(f"[Crawl] Hết {budget}s: đi tiếp không chờ {names}; kết quả của sàn chậm sẽ nạp vào kho RAG")
            search_sources.keep_in_background(asyncio.create_task(_store_late_results(late, tasks)))
        return per_platform

    async def _apply_categories(
        self, per_platform: dict[str, list[RawProduct]], criteria: UniversalSearchCriteria | None
    ) -> None:
        """Gán ngành hàng theo danh mục của sàn (CategoryResolver) và bỏ phụ kiện khi người dùng không tìm phụ kiện.

        Nhiều món là sản phẩm chính với người mua nhưng sàn xếp vào "Phụ kiện" (bàn phím, chuột, sạc dự phòng...):
        nếu bỏ phụ kiện làm mất SẠCH kết quả thì giữ lại, để bước LLM lọc + chấm (search_sources.screen) xét theo
        đúng câu hỏi thay vì báo "không tìm thấy".
        """
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
        main: dict[str, list[RawProduct]] = {}
        with_accessories: dict[str, list[RawProduct]] = {}
        for pid, lst in per_platform.items():
            main[pid], with_accessories[pid] = [], []
            for p in lst:
                mapping = category_resolver.lookup(p)
                if mapping is None:
                    item = p  # chưa rõ: để bước LLM lọc phía sau quyết định
                else:
                    item = {**p, "category": mapping.category, "name": with_noun(p.get("name", ""), mapping.noun)}
                with_accessories[pid].append(item)
                if mapping is None or wants_accessory or not mapping.is_accessory:
                    main[pid].append(item)
        if any(main.values()) or not any(with_accessories.values()):
            per_platform.update(main)
            return
        logger.info("Mọi kết quả đều thuộc danh mục phụ kiện của sàn: giữ lại để LLM xét theo câu hỏi")
        per_platform.update(with_accessories)
