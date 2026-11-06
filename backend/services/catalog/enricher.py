"""Bồi đắp thông tin chi tiết cho sản phẩm từ trang chi tiết của sàn (Mức 2 - tư vấn mua sắm)."""
import time
import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx

from services.catalog.platforms import get_platform

logger = logging.getLogger("product_enricher")

DETAIL_CACHE_TTL_SECONDS = 6 * 3600


class ProductEnricher:
    # timeout ngắn: trang chậm không được kéo dài cả lượt tư vấn
    def __init__(self, concurrency: int = 6, timeout: float = 6.0):
        self.concurrency = concurrency
        self.timeout = timeout
        self._cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._pending: set = set()  # lần tải vượt thời gian chờ, tiếp tục chạy ở nền
        self._ssl_context = httpx.create_ssl_context()

    def _cache_get(self, key: str) -> Optional[Dict[str, Any]]:
        hit = self._cache.get(key)
        if hit and time.time() - hit[0] < DETAIL_CACHE_TTL_SECONDS:
            return hit[1]
        return None

    @staticmethod
    def _cache_key(product: Dict[str, Any]) -> Optional[str]:
        platform = get_platform(product.get("platform"))
        return platform.detail_cache_key(product) if platform else None

    async def _fetch_detail(self, client: httpx.AsyncClient, product: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        platform, key = get_platform(product.get("platform")), self._cache_key(product)
        if not platform or not key:
            return None
        try:
            detail = await platform.fetch_detail(client, product)
        except Exception as e:
            logger.warning(f"[Enricher] Không lấy được chi tiết '{product.get('name', '')[:50]}': {e}")
            return None
        if detail is not None:
            self._cache[key] = (time.time(), detail)
        return detail

    async def fetch_current_price(self, product: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """Giá bán hiện tại của một sản phẩm, đọc trực tiếp từ sàn (không qua cache), dùng cho theo dõi giá:"""
        platform = get_platform(product.get("platform"))
        if not platform:
            return None
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=self.timeout) as client:
                return await platform.fetch_price(client, product)
        except Exception as e:
            logger.warning(f"[Enricher] Không đọc được giá hiện tại '{product.get('name', '')[:50]}': {e}")
        return None

    @staticmethod
    def merge_detail(product: Dict[str, Any], detail: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(product)
        specs = merged.get("specs")
        specs = dict(specs) if isinstance(specs, dict) else ({"Tóm tắt": specs} if isinstance(specs, str) and specs.strip() else {})
        for k, v in (detail.get("specs") or {}).items():
            specs[k] = v
        merged["specs"] = specs
        if detail.get("warranty"):
            merged["warranty"] = detail["warranty"]
        if detail.get("returnPolicy"):
            merged["returnPolicy"] = detail["returnPolicy"]
        if detail.get("rating"):  # trang danh sách CellphoneS không có điểm đánh giá
            merged["rating"] = detail["rating"]
            if detail.get("reviewsCount"):
                merged["reviewsCount"] = f"{detail['reviewsCount']} đánh giá"
        merged["detailFetched"] = bool(detail.get("specs"))
        return merged

    async def _fetch_many(self, products: List[Dict[str, Any]], indices: List[int], results: List) -> None:
        """Tải các trang chi tiết; ghi dần vào `results` để bên gọi lấy được phần đã xong khi hết thời gian."""
        sem = asyncio.Semaphore(self.concurrency)
        async with httpx.AsyncClient(follow_redirects=True, timeout=self.timeout, verify=self._ssl_context) as client:
            async def run_one(idx: int):
                async with sem:
                    detail = await self._fetch_detail(client, products[idx])
                    results.append((idx, detail))

            await asyncio.gather(*(run_one(i) for i in indices))

    async def enrich(
        self,
        products: List[Dict[str, Any]],
        max_items: int = 10,
        budget_seconds: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Bồi đắp tối đa `max_items` sản phẩm đầu danh sách;"""
        if not products:
            return products
        targets = [
            i for i, p in enumerate(products[:max_items])
            if not p.get("detailFetched") and self._cache_key(p)
        ]
        if not targets:
            return products

        results: List[Tuple[int, Optional[Dict[str, Any]]]] = []
        to_fetch: List[int] = []
        for i in targets:
            cached = self._cache_get(self._cache_key(products[i]))
            if cached is not None:
                results.append((i, cached))
            else:
                to_fetch.append(i)

        if to_fetch:
            job = asyncio.create_task(self._fetch_many(products, to_fetch, results))
            done, _ = await asyncio.wait({job}, timeout=budget_seconds)
            if not done:
                self._pending.add(job)
                job.add_done_callback(self._pending.discard)
                logger.info(f"[Enricher] Hết {budget_seconds}s: {len(results)}/{len(targets)} trang đã xong, phần còn lại tải ở nền.")

        enriched = list(products)
        ok = 0
        for idx, detail in list(results):
            if detail:
                enriched[idx] = self.merge_detail(enriched[idx], detail)
                ok += enriched[idx].get("detailFetched", False)
        logger.info(f"[Enricher] Đã lấy thông số chi tiết cho {ok}/{len(targets)} sản phẩm ({len(to_fetch)} tải mới).")
        return enriched


product_enricher = ProductEnricher()
