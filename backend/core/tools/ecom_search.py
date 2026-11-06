import re
import logging
import asyncio
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from .base import BaseTool
from ..state import UniversalSearchCriteria
from database.repositories import product_repository
from services.catalog.data_processor import data_processor
from services.catalog.semantic_filter import semantic_filter
from services.rag import rag_service
from services.catalog.platforms import PlatformAdapter, all_platforms, display_names, resolve_targets
from services.catalog.platforms.common import strip_attribute_terms, within_price
from services.catalog.category_resolver import category_resolver, with_noun
from services.pricing import guardrails as price_guardrails
from services.catalog.enricher import product_enricher
from services.catalog.ranker import rank_products, verifiable_attributes
from datetime import datetime, timezone

logger = logging.getLogger("ecom_search")

PRICE_PHRASE_RE = re.compile(
    r"(?:\b(?:dưới|trên|từ|khoảng|tầm|giá|tối đa|không quá)\s+)?"
    r"\d+(?:[.,]\d+)?\s*(?:-|–|đến|tới)?\s*\d*(?:[.,]\d+)?\s*(?:triệu|tr|củ|k|nghìn|ngàn)\b",
    re.IGNORECASE,
)

DETAIL_BUDGET_SECONDS = 2.0
CATEGORY_BUDGET_SECONDS = 6.0

_background_tasks: set = set()


@dataclass
class _Search:
    """Tham số dùng chung cho mọi bước của một lượt tìm kiếm."""
    keyword: str
    criteria: Optional[UniversalSearchCriteria]
    category: str
    target_platform: str  # sàn thực sự tìm ("all" = mọi sàn)
    limit: int
    notes: List[str]


def _interleave(lists, cap: int) -> List[Dict[str, Any]]:
    """Đan xen kết quả các sàn (1 của sàn A, 1 của sàn B...) để so sánh giá công bằng; tối đa `cap` sản phẩm."""
    lists = [l for l in lists if l]
    out: List[Dict[str, Any]] = []
    for i in range(max((len(l) for l in lists), default=0)):
        out += [l[i] for l in lists if i < len(l)]
    return out[:cap]


def _run_in_background(coro) -> None:
    """Chạy việc không ảnh hưởng tới câu trả lời hiện tại (VD lưu kho RAG) mà không bắt người dùng chờ."""
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


class EcomSearchTool(BaseTool):
    name = "ecom_search"
    description = f"Tìm kiếm sản phẩm thực tế từ các sàn và hệ thống bán lẻ ({display_names()})"


    def __init__(self, platforms: Optional[List[PlatformAdapter]] = None):
        self.platforms = platforms if platforms is not None else all_platforms()

    def optimize_crawler_query(self, query: str, criteria: Optional[UniversalSearchCriteria]) -> str:
        """[Tầng 1 - Universal Data-Driven] Tối ưu hóa từ khóa tìm kiếm cho crawler."""
        q = (criteria.cleaned_query if (criteria and criteria.cleaned_query) else query).strip()
        q = re.sub(PRICE_PHRASE_RE, " ", q)
        q = re.sub(r"\s+", " ", q).strip() or query.strip()
        q_lower = q.lower()

        if criteria and criteria.is_accessory:
            return q

        if criteria and criteria.target_entity:
            entity = criteria.target_entity.strip().lower()
            if entity and entity not in q_lower:
                return f"{entity} {q}"


        return q

    def _annotate_attribute_match(
        self,
        products: List[Dict[str, Any]],
        criteria: Optional[UniversalSearchCriteria],
        notes: List[str]
    ) -> List[Dict[str, Any]]:
        """Kiểm tra các thuộc tính kỹ thuật người dùng yêu cầu (VD:"""
        if not products or not criteria or not criteria.attributes:
            return products
        wanted = verifiable_attributes(criteria)
        if not wanted:
            return products

        def norm(s: str) -> str:
            return re.sub(r"[\s\-_]+", "", s.lower())

        verified, unverified = [], []
        for p in products:
            haystack = norm(f"{p.get('name', '')} {p.get('specs', '')} {p.get('aiSummary', '')}")
            if all(norm(v) in haystack for v in wanted.values()):
                verified.append(p)
            else:
                unverified.append(p)

        wanted_text = ", ".join(f"{k}={v}" for k, v in wanted.items())
        if not verified:
            notes.append(
                f"KHÔNG sản phẩm nào xác nhận được yêu cầu kỹ thuật ({wanted_text}) từ tên/thông số thu thập được. "
                f"Không được khẳng định các sản phẩm dưới đây đáp ứng yêu cầu này."
            )
        elif unverified:
            notes.append(
                f"Chỉ {len(verified)}/{len(products)} sản phẩm xác nhận có {wanted_text} (xếp đầu danh sách); "
                f"các sản phẩm còn lại CHƯA xác minh được thông số này."
            )
        return verified + unverified

    @staticmethod
    def _freshness_note(products: List[Dict[str, Any]]) -> Optional[str]:
        """Ghi chú độ mới của dữ liệu nếu lấy từ cache/kho lưu (có updatedAt)."""
        ages = []
        now = datetime.now(timezone.utc)
        for p in products:
            raw = p.get("updatedAt")
            if not raw:
                continue
            try:
                ts = datetime.fromtimestamp(float(raw), tz=timezone.utc) if str(raw).replace(".", "").isdigit() \
                    else datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)  # DB lưu datetime.utcnow() không kèm múi giờ
                ages.append((now - ts).total_seconds() / 3600)
            except (ValueError, OSError):
                continue
        if not ages:
            return None
        oldest = max(ages)
        if oldest < 1:
            return None
        age_text = f"{oldest:.0f} giờ" if oldest < 48 else f"{oldest / 24:.0f} ngày"
        return f"Dữ liệu giá cũ nhất trong danh sách được cập nhật cách đây khoảng {age_text}; giá thực tế có thể đã thay đổi."

    async def _finalize(
        self,
        products: List[Dict[str, Any]],
        criteria: Optional[UniversalSearchCriteria],
        notes: List[str],
        limit: int,
        detail_budget: float = DETAIL_BUDGET_SECONDS
    ) -> List[Dict[str, Any]]:
        """Bước chung cho mọi nguồn (cache, RAG, cào trực tiếp):"""
        if not products:
            return products
        products = await product_enricher.enrich(products, max_items=max(limit * 2, 8), budget_seconds=detail_budget)
        references = await product_repository.get_reference_prices([p.get("name", "") for p in products])
        products, rejected = price_guardrails.screen_products(products, references)
        if rejected:
            notes.append(f"Đã loại {len(rejected)} sản phẩm có giá bất thường (nghi đọc nhầm giá trả góp, phụ kiện hoặc lỗi trang).")
        products = self._annotate_attribute_match(products, criteria, notes)
        if criteria:
            products, rank_notes = rank_products(products, criteria)
            notes.extend(rank_notes)
        freshness = self._freshness_note(products[:limit])
        if freshness and freshness not in notes:
            notes.append(freshness)
        return products[:limit]

    async def _store_in_rag(self, products: List[Dict[str, Any]]) -> None:
        try:
            stored = await asyncio.to_thread(rag_service.upsert_products, products)
            logger.info(f"[Self-Populating RAG] Đã nạp {stored}/{len(products)} sản phẩm mới cào vào ChromaDB!")
        except Exception as rag_upsert_err:
            logger.warning(f"Lỗi tự động nạp vào ChromaDB: {rag_upsert_err}")

    async def _crawl(
        self,
        search_keyword: str,
        criteria: Optional[UniversalSearchCriteria],
        platform: str,
        limit: int,
        notes: List[str],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
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

    def _target_platforms(self, platform: str, criteria: Optional[UniversalSearchCriteria],
                          notes: List[str]) -> List[PlatformAdapter]:
        """Sàn cần tìm: sàn chọn trên giao diện / router trích từ câu hỏi; sàn không hỗ trợ thì tìm mọi sàn."""
        wanted = [platform] if (platform and platform != "all") else ((criteria.target_platforms or ["all"]) if criteria else ["all"])
        target_ids = {p.id for p in resolve_targets(wanted)}
        targets = [p for p in self.platforms if p.id in target_ids]
        if targets:
            return targets
        notes.append(f"Hệ thống không tìm trên sàn này; kết quả lấy từ {display_names()}.")
        return list(self.platforms)

    @staticmethod
    async def _search_platforms(targets, query, criteria, cap, notes, user_query) -> Dict[str, List[Dict[str, Any]]]:
        """Gọi song song các sàn; sàn lỗi trả về danh sách rỗng, không làm hỏng cả lượt."""
        results = await asyncio.gather(
            *(p.search(query, criteria, cap, notes, user_query=user_query) for p in targets), return_exceptions=True)
        per_platform: Dict[str, List[Dict[str, Any]]] = {}
        for p, res in zip(targets, results):
            if isinstance(res, Exception):
                logger.warning(f"[{p.name}] Lỗi khi tìm kiếm: {res}")
            per_platform[p.id] = res if isinstance(res, list) else []
        return per_platform

    async def _apply_categories(self, per_platform: Dict[str, List[Dict[str, Any]]],
                                criteria: Optional[UniversalSearchCriteria]) -> None:
        """Gán ngành hàng theo danh mục của sàn (CategoryResolver) và bỏ phụ kiện khi người dùng không tìm phụ kiện."""
        items = [p for lst in per_platform.values() for p in lst]
        if not items:
            return
        task = asyncio.create_task(category_resolver.resolve(items))
        try:
            await asyncio.wait_for(asyncio.shield(task), CATEGORY_BUDGET_SECONDS)
        except asyncio.TimeoutError:
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)
            logger.info("Quy đổi danh mục mới chưa xong, tiếp tục ở nền; sản phẩm lượt này giữ ngành hàng tạm")
        except Exception as e:
            logger.warning(f"Lỗi quy đổi danh mục: {e}")
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

    async def run(
        self,
        query: str,
        category: str = "all",
        criteria: Optional[UniversalSearchCriteria] = None,
        platform: str = "all",
        limit: int = 6,
        force_refresh: bool = False,
        notes: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Tìm sản phẩm thật trên các sàn:"""
        search = self._prepare(query, category, criteria, platform, limit, notes)
        if search is None:
            return []

        if not force_refresh:
            cached = await self._from_cache(search)
            if cached:
                return cached

        crawl_notes: List[str] = []
        crawl = asyncio.create_task(self._crawl(search.keyword, criteria, platform, limit, crawl_notes))
        if not force_refresh:
            stored = await self._from_rag(search)
            if stored:
                crawl.cancel()
                return stored

        products = await self._from_crawl(search, crawl, crawl_notes)
        await self._remember(search, products)
        return products

    def _prepare(self, query, category, criteria, platform, limit, notes) -> Optional[_Search]:
        """Từ khóa thực sự tìm và sàn mục tiêu (sàn chọn trên giao diện, hoặc sàn router trích từ câu hỏi)."""
        keyword = criteria.cleaned_query if (criteria and criteria.cleaned_query) else query
        if not keyword.strip():
            return None
        target = platform.lower().strip() if (platform and platform != "all") else "all"
        if target == "all" and criteria and criteria.target_platforms:
            target = criteria.target_platforms[0].lower().strip()
        return _Search(keyword=keyword, criteria=criteria, category=category, target_platform=target,
                       limit=limit, notes=notes if notes is not None else [])

    async def _from_cache(self, s: _Search) -> Optional[List[Dict[str, Any]]]:
        """Kết quả đã lưu cho đúng từ khóa (SQLite, < 5 ms), lọc lại theo khoảng giá của lượt này."""
        try:
            cached = await product_repository.get_cached_search(query=s.keyword, platform=s.target_platform)
        except Exception as e:
            logger.warning(f"Lỗi kiểm tra cache SQLite: {e}")
            return None
        hits = [p for p in cached or [] if within_price(float(p.get("currentPrice", 0)), s.criteria)]
        if not hits:
            return None
        logger.info(f"[SQLite Cache Hit] {len(hits)} sản phẩm cho '{s.keyword}' (platform={s.target_platform})")
        return await self._finalize(hits, s.criteria, s.notes, s.limit, detail_budget=0)

    async def _from_rag(self, s: _Search) -> Optional[List[Dict[str, Any]]]:
        """Sản phẩm tương đồng trong kho RAG, đã qua bộ lọc ngữ nghĩa; None nếu kho không có gì dùng được."""
        c = s.criteria
        category = c.category if (c and c.category != "all") else (s.category if s.category != "all" else None)
        try:
            found = await asyncio.to_thread(
                rag_service.search, query=s.keyword, category=category,
                min_price=c.min_price if c else None, max_price=c.max_price if c else None,
                platform=s.target_platform if s.target_platform != "all" else None, limit=s.limit * 2,
            )
            found = await self._semantic_filter(found, s) if found else []
        except Exception as e:
            logger.warning(f"Lỗi kiểm tra RAG ChromaDB: {e}")
            return None
        if not found:
            return None
        logger.info(f"[RAG Vector Hit] {len(found)} sản phẩm từ ChromaDB cho '{s.keyword}' "
                    f"(khớp cao nhất {found[0].get('aiMatchScore')}%)")
        s.notes.append(
            "Kết quả lấy từ kho dữ liệu đã thu thập trước đó (tìm theo độ tương đồng), "
            "không phải quét trực tiếp lúc này: giá và tình trạng hàng có thể đã thay đổi, "
            "và có thể không khớp chính xác tên model người dùng hỏi."
        )
        return await self._finalize(found, s.criteria, s.notes, s.limit)

    async def _from_crawl(self, s: _Search, crawl: "asyncio.Task", crawl_notes: List[str]) -> List[Dict[str, Any]]:
        """Kết quả cào trực tiếp (đã chạy song song từ trước): lọc ngữ nghĩa rồi xếp hạng."""
        products, source_counts = await crawl
        s.notes.extend(crawl_notes)
        products = await self._semantic_filter(products, s)
        logger.info(f"Tìm kiếm thực tế cho '{s.keyword}': {source_counts} -> sau thẩm định AI: {len(products)} sản phẩm")
        return await self._finalize(products, s.criteria, s.notes, s.limit)

    async def _semantic_filter(self, products: List[Dict[str, Any]], s: _Search) -> List[Dict[str, Any]]:
        kept, _ = await semantic_filter.filter_products(
            query=strip_attribute_terms(s.keyword, s.criteria) or s.keyword, products=products, criteria=s.criteria)
        return kept

    async def _remember(self, s: _Search, products: List[Dict[str, Any]]) -> None:
        """Lưu kết quả cào: kho RAG (tính embedding ở nền, chỉ phục vụ lần sau) và cache SQLite 2 giờ."""
        if not products:
            return
        _run_in_background(self._store_in_rag(products))
        try:
            await product_repository.save_search_cache(
                query=s.keyword, platform=s.target_platform, products=products, ttl_hours=2)
        except Exception as e:
            logger.warning(f"Lỗi tự động lưu cache CSDL: {e}")
