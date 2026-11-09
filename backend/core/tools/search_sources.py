"""3 nguồn kết quả của một lượt tìm, theo thứ tự ưu tiên, và việc lưu kết quả cho lần sau.

    1. from_cache()  cache SQLite đúng từ khóa (< 5 ms)
    2. from_rag()    sản phẩm tương đồng trong kho RAG (chạy song song với việc cào)
    3. from_crawl()  cào trực tiếp các sàn
    remember()       lưu kết quả cào vào kho RAG (ở nền) và cache SQLite 2 giờ

RAG và cào đi qua screen() (đọc trang chi tiết, rồi một lần gọi LLM vừa lọc phụ kiện vừa chấm mức hợp nhu cầu);
mọi nguồn đều đi qua tool._finalize() (loại giá bất thường, đối chiếu thông số, xếp hạng).
"""

import asyncio
import logging
from dataclasses import dataclass

from database.repositories import product_repository
from integrations.platforms.common import strip_attribute_terms, within_price
from services.catalog import spec_fit
from services.catalog.enricher import product_enricher
from services.catalog.ranker import verifiable_attributes
from services.rag import rag_service
from shared.exceptions import DatabaseError
from shared.fallback import fallback
from shared.types import RawProduct

from ..state import UniversalSearchCriteria

logger = logging.getLogger("search_sources")

CACHE_TTL_HOURS = 2
DETAIL_BUDGET_SECONDS = 2.0  # thời gian tối đa chờ đọc trang chi tiết trong một lượt
MAX_SCREEN_DETAILS = 16  # số trang chi tiết tối đa đọc trong lúc lọc

# Giữ tham chiếu tới việc chạy nền (asyncio chỉ giữ tham chiếu yếu, task có thể bị thu hồi giữa chừng)
_background_tasks: set = set()


@dataclass
class SearchRequest:
    """Tham số dùng chung cho mọi bước của một lượt tìm kiếm."""

    keyword: str
    criteria: UniversalSearchCriteria | None
    category: str
    target_platform: str  # sàn thực sự tìm ("all" = mọi sàn)
    limit: int
    notes: list[str]


def _log_background_error(task: "asyncio.Task") -> None:
    """Việc chạy nền không có ai chờ kết quả: lỗi phải được ghi log tại đây, không thì bị mất."""
    if not task.cancelled() and task.exception() is not None:
        logger.error("Lỗi trong tác vụ chạy nền", exc_info=task.exception())


def keep_in_background(task: "asyncio.Task") -> None:
    """Để một task tiếp tục chạy ở nền (giữ tham chiếu, ghi log nếu lỗi)."""
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    task.add_done_callback(_log_background_error)


def run_in_background(coro) -> None:
    """Chạy việc không ảnh hưởng tới câu trả lời hiện tại (VD lưu kho RAG) mà không bắt người dùng chờ."""
    keep_in_background(asyncio.create_task(coro))


async def screen(products: list[RawProduct], s: SearchRequest) -> list[RawProduct]:
    """Đọc trang chi tiết, rồi MỘT lần gọi LLM vừa bỏ phụ kiện ăn theo / hàng khác loại vừa chấm mức hợp nhu cầu.

    LLM lỗi thì giữ nguyên danh sách, không có điểm hợp nhu cầu (spec_fit.screen).
    """
    enriched = await product_enricher.enrich(
        products, max_items=min(len(products), MAX_SCREEN_DETAILS), budget_seconds=DETAIL_BUDGET_SECONDS
    )
    query = strip_attribute_terms(s.keyword, s.criteria) or s.keyword
    wanted = verifiable_attributes(s.criteria) if s.criteria else {}
    return await spec_fit.screen(enriched, s.criteria, query, wanted)


async def from_cache(tool, s: SearchRequest) -> list[RawProduct] | None:
    """Kết quả đã lưu cho đúng từ khóa, lọc lại theo khoảng giá của lượt này; None nếu không có."""
    cached = None
    with fallback(DatabaseError, "Lỗi kiểm tra cache SQLite", logger):
        cached = await product_repository.get_cached_search(query=s.keyword, platform=s.target_platform)
    hits = [p for p in cached or [] if within_price(float(p.get("currentPrice", 0)), s.criteria)]
    if not hits:
        return None
    logger.info(f"[SQLite Cache Hit] {len(hits)} sản phẩm cho '{s.keyword}' (platform={s.target_platform})")
    return await tool._finalize(hits, s.criteria, s.notes, s.limit, detail_budget=0)


async def from_rag(tool, s: SearchRequest) -> list[RawProduct] | None:
    """Sản phẩm tương đồng trong kho RAG, đã qua bộ lọc ngữ nghĩa; None nếu kho không có gì dùng được."""
    c = s.criteria
    category = c.category if (c and c.category != "all") else (s.category if s.category != "all" else None)
    # rag_service.search trả [] khi ChromaDB lỗi; bộ lọc ngữ nghĩa giữ nguyên danh sách khi LLM lỗi
    found = await asyncio.to_thread(
        rag_service.search,
        query=s.keyword,
        category=category,
        min_price=c.min_price if c else None,
        max_price=c.max_price if c else None,
        platform=s.target_platform if s.target_platform != "all" else None,
        limit=s.limit * 2,
    )
    found = await screen(found, s) if found else []
    if not found:
        return None
    logger.info(
        f"[RAG Vector Hit] {len(found)} sản phẩm từ ChromaDB cho '{s.keyword}' "
        f"(khớp cao nhất {found[0].get('aiMatchScore')}%)"
    )
    s.notes.append(
        "Kết quả lấy từ kho dữ liệu đã thu thập trước đó (tìm theo độ tương đồng), "
        "không phải quét trực tiếp lúc này: giá và tình trạng hàng có thể đã thay đổi, "
        "và có thể không khớp chính xác tên model người dùng hỏi."
    )
    return await tool._finalize(found, s.criteria, s.notes, s.limit, screened=True)


async def from_crawl(tool, s: SearchRequest, crawl: "asyncio.Task", crawl_notes: list[str]) -> list[RawProduct]:
    """Kết quả cào trực tiếp (task đã chạy song song từ trước): lọc ngữ nghĩa + đọc chi tiết rồi xếp hạng."""
    products, source_counts = await crawl
    s.notes.extend(crawl_notes)
    products = await screen(products, s) if products else []
    logger.info(f"Tìm kiếm thực tế cho '{s.keyword}': {source_counts} -> sau thẩm định AI: {len(products)} sản phẩm")
    return await tool._finalize(products, s.criteria, s.notes, s.limit, screened=True)


async def store_in_rag(products: list[RawProduct]) -> None:
    """rag_service tự bỏ qua lỗi ChromaDB / embedding (trả về 0)."""
    stored = await asyncio.to_thread(rag_service.upsert_products, products)
    logger.info(f"[Self-Populating RAG] Đã nạp {stored}/{len(products)} sản phẩm mới cào vào ChromaDB!")


async def remember(s: SearchRequest, products: list[RawProduct]) -> None:
    """Lưu kết quả cào: kho RAG (tính embedding ở nền, chỉ phục vụ lần sau) và cache SQLite."""
    if not products:
        return
    run_in_background(store_in_rag(products))
    with fallback(DatabaseError, "Lỗi tự động lưu cache CSDL", logger):
        await product_repository.save_search_cache(
            query=s.keyword, platform=s.target_platform, products=products, ttl_hours=CACHE_TTL_HOURS
        )
