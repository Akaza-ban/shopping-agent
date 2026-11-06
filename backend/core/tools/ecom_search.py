import re
import json
import logging
import asyncio
import subprocess
import urllib.parse
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from .base import BaseTool
from ..state import UniversalSearchCriteria
from database.repositories import product_repository

logger = logging.getLogger("ecom_search")


class EcomSearchTool(BaseTool):
    name = "ecom_search"
    description = "Tìm kiếm sản phẩm thực tế từ các sàn và hệ thống bán lẻ (Tiki, Lazada, Shopee, Thế Giới Di Động, Điện Máy Xanh)"


    def __init__(self):
        self.tiki_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://tiki.vn/"
        }

    async def _search_tiki(
        self,
        search_keyword: str,
        criteria: Optional[UniversalSearchCriteria],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Gọi API tìm kiếm thực tế từ sàn Tiki."""
        tiki_products: List[Dict[str, Any]] = []
        try:
            params = {"q": search_keyword, "limit": limit * 2}
            if criteria:
                if criteria.min_price and criteria.max_price:
                    params["price"] = f"{int(criteria.min_price)},{int(criteria.max_price)}"
                elif criteria.min_price:
                    params["price"] = f"{int(criteria.min_price)},1000000000"
                elif criteria.max_price:
                    params["price"] = f"0,{int(criteria.max_price)}"

            async with httpx.AsyncClient(headers=self.tiki_headers, follow_redirects=True, timeout=8.0) as client:
                resp = await client.get(
                    "https://tiki.vn/api/v2/products",
                    params=params
                )
                if resp.status_code == 200:
                    raw_data = resp.json().get("data", [])
                    for item in raw_data:
                        curr_price = float(item.get("price", 0))
                        orig_price = float(item.get("original_price") or curr_price)
                        
                        # Bộ lọc giá theo criteria của người dùng
                        if criteria:
                            if criteria.max_price and curr_price > criteria.max_price:
                                continue
                            if criteria.min_price and curr_price < criteria.min_price:
                                continue

                        rating = float(item.get("rating_average") or 5.0)
                        reviews_count = item.get("review_count") or 0
                        thumb = item.get("thumbnail_url") or ""
                        url_path = item.get("url_path") or ""

                        product_entry = {
                            "id": f"tiki-{item.get('id', '')}",
                            "name": str(item.get("name", "")).strip(),
                            "category": criteria.category if criteria else "all",
                            "categoryName": criteria.category_name if criteria else "Sản phẩm",
                            "platform": "tiki",
                            "platformName": "Tiki Trading",
                            "platformBadgeColor": "#1a94ff",
                            "platformBadgeBg": "rgba(26, 148, 255, 0.15)",
                            "aiMatchScore": 95 if rating >= 4.5 else 85,
                            "originalPrice": orig_price,
                            "currentPrice": curr_price,
                            "discountPercent": int(item.get("discount_rate") or 0),
                            "rating": rating,
                            "reviewsCount": f"{reviews_count} đánh giá",
                            "sku": str(item.get("sku") or f"TIKI-{item.get('id')}"),
                            "image": thumb,
                            "aiSummary": f"Sản phẩm thực tế trên Tiki: {item.get('name')}. Đánh giá {rating}/5 với {reviews_count} lượt mua.",
                            "warranty": "Chính hãng Tiki",
                            "deliveryTag": "TikiNOW",
                            "selected": False,
                            "externalUrl": f"https://tiki.vn/{url_path}" if url_path else "https://tiki.vn"
                        }
                        tiki_products.append(product_entry)
                        if len(tiki_products) >= limit:
                            break
        except Exception as e:
            logger.error(f"Lỗi khi tìm kiếm Tiki: {e}")

        return tiki_products

    async def _search_lazada(
        self,
        search_keyword: str,
        criteria: Optional[UniversalSearchCriteria],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Gọi API Catalog thực tế từ sàn Lazada qua native async client."""
        lazada_products: List[Dict[str, Any]] = []
        try:
            encoded_q = urllib.parse.quote(search_keyword)
            api_url = f"https://www.lazada.vn/catalog/?q={encoded_q}&ajax=true"

            # Tích hợp bộ lọc giá trực tiếp vào query param của Lazada
            if criteria:
                if criteria.min_price and criteria.max_price:
                    api_url += f"&price={int(criteria.min_price)}-{int(criteria.max_price)}"
                elif criteria.max_price:
                    api_url += f"&price=-{int(criteria.max_price)}"
                elif criteria.min_price:
                    api_url += f"&price={int(criteria.min_price)}-"

            cmd = [
                "curl.exe", "-s", "-L",
                "--compressed",
                "--max-time", "6",
                "--connect-timeout", "3",
                "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "-H", "Referer: https://www.lazada.vn/",
                "-H", "x-requested-with: XMLHttpRequest",
                "-H", "Accept: application/json, text/plain, */*",
                api_url
            ]

            def _exec_curl():
                return subprocess.run(cmd, capture_output=True, timeout=7.0)

            try:
                proc_res = await asyncio.to_thread(_exec_curl)
            except subprocess.TimeoutExpired:
                logger.warning("Lazada search timed out sau 7s.")
                return []
            except Exception as proc_err:
                logger.warning(f"Lỗi khi chạy curl Lazada: {proc_err}")
                return []

            if proc_res.returncode == 0 and proc_res.stdout:
                raw_text = proc_res.stdout.decode("utf-8", errors="ignore").strip()
                if not raw_text or not (raw_text.startswith("{") or raw_text.startswith("[")):
                    return []
                try:
                    res_data = json.loads(raw_text)
                except Exception as json_err:
                    logger.warning(f"Không thể parse JSON từ Lazada: {json_err}")
                    return []

                items = res_data.get("mods", {}).get("listItems", [])
                
                for item in items:
                    raw_price = item.get("price")
                    if raw_price is None:
                        continue
                    try:
                        curr_price = float(raw_price)
                    except (ValueError, TypeError):
                        continue

                    # Fallback lọc giá nếu query param chưa phủ hết
                    if criteria:
                        if criteria.max_price and curr_price > criteria.max_price:
                            continue
                        if criteria.min_price and curr_price < criteria.min_price:
                            continue

                    orig_price_raw = item.get("originalPrice") or curr_price
                    try:
                        orig_price = float(orig_price_raw)
                    except (ValueError, TypeError):
                        orig_price = curr_price

                    # Tính toán tỷ lệ giảm giá (%)
                    discount_pct = 0
                    discount_str = str(item.get("discount") or "")
                    disc_match = re.search(r"(\d+)%", discount_str)
                    if disc_match:
                        discount_pct = int(disc_match.group(1))
                    elif orig_price > curr_price and orig_price > 0:
                        discount_pct = int(round((1 - curr_price / orig_price) * 100))

                    try:
                        rating = float(item.get("ratingScore") or 5.0)
                    except (ValueError, TypeError):
                        rating = 5.0

                    reviews_count = item.get("review") or 0
                    item_id = str(item.get("itemId") or item.get("nid") or "")
                    name = str(item.get("name") or "").strip()
                    thumb = item.get("image") or ""
                    seller = item.get("sellerName") or "Lazada Seller"
                    item_url = item.get("itemUrl") or ""
                    if item_url.startswith("//"):
                        item_url = f"https:{item_url}"
                    elif not item_url.startswith("http"):
                        item_url = f"https://www.lazada.vn{item_url}"

                    is_lazmall = "lazmall" in str(item.get("icons", [])).lower() or "official" in seller.lower()

                    product_entry = {
                        "id": f"lazada-{item_id}",
                        "name": name,
                        "category": criteria.category if criteria else "all",
                        "categoryName": criteria.category_name if criteria else "Sản phẩm",
                        "platform": "lazada",
                        "platformName": "LazMall" if is_lazmall else "Lazada",
                        "platformBadgeColor": "#0f156d",
                        "platformBadgeBg": "rgba(15, 21, 109, 0.15)",
                        "aiMatchScore": 95 if rating >= 4.5 else 85,
                        "originalPrice": orig_price,
                        "currentPrice": curr_price,
                        "discountPercent": discount_pct,
                        "rating": rating,
                        "reviewsCount": f"{reviews_count} đánh giá",
                        "sku": str(item.get("sku") or f"LAZ-{item_id}"),
                        "image": thumb,
                        "aiSummary": f"Sản phẩm thực tế trên Lazada từ gian hàng {seller}: {name}. Đánh giá {rating}/5.",
                        "warranty": "Chính hãng 100%" if is_lazmall else "Theo chính sách gian hàng",
                        "deliveryTag": "LazFlash / Giao nhanh",
                        "selected": False,
                        "externalUrl": item_url
                    }
                    lazada_products.append(product_entry)
                    if len(lazada_products) >= limit:
                        break

        except Exception as e:
            logger.error(f"Lỗi khi tìm kiếm Lazada ({type(e).__name__}): {e}", exc_info=True)

        return lazada_products

    async def _search_shopee(
        self,
        search_keyword: str,
        criteria: Optional[UniversalSearchCriteria],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Gọi API tìm kiếm sàn Shopee.
        Shopee áp dụng hệ thống bảo mật SeaShield/WAF (yêu cầu Captcha trượt và token af-ac-enc-dat).
        Hệ thống gửi request chuẩn; nếu gặp kiểm tra Captcha (error 90309999), sẽ xử lý an toàn và không gây crash.
        """
        shopee_products: List[Dict[str, Any]] = []
        try:
            encoded_q = urllib.parse.quote(search_keyword)
            api_url = (
                f"https://shopee.vn/api/v4/search/search_items?"
                f"by=relevancy&keyword={encoded_q}&limit={limit}&newest=0&order=desc"
                f"&page_type=search&scenario=PAGE_GLOBAL_SEARCH&version=2"
            )
            cmd = [
                "curl.exe", "-s", "-L",
                "--compressed",
                "--max-time", "6",
                "--connect-timeout", "3",
                "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                "-H", "Referer: https://shopee.vn/",
                "-H", "Accept: application/json",
                "-H", "x-api-source: pc",
                "-H", "x-shopee-language: vi",
                "-H", "x-requested-with: XMLHttpRequest",
                api_url
            ]

            def _exec_curl():
                return subprocess.run(cmd, capture_output=True, timeout=7.0)

            proc_res = await asyncio.to_thread(_exec_curl)
            if proc_res.returncode == 0 and proc_res.stdout:
                raw_text = proc_res.stdout.decode("utf-8", errors="ignore").strip()
                if not raw_text or not (raw_text.startswith("{") or raw_text.startswith("[")):
                    return []
                try:
                    res_data = json.loads(raw_text)
                except Exception:
                    return []

                # Trường hợp Shopee kích hoạt thử thách xác minh bot (Error 90309999)
                if res_data.get("error") == 90309999 or res_data.get("action_type") == 2:
                    logger.warning("Shopee kích hoạt cơ chế bảo vệ SeaShield/WAF (Yêu cầu xác minh người dùng). Cần Open API Token hoặc dán link sản phẩm trực tiếp.")
                    return []

                raw_items = res_data.get("items", []) or []
                for entry in raw_items:
                    basic = entry.get("item_basic", {})
                    if not basic:
                        continue
                    item_id = str(basic.get("itemid", ""))
                    shop_id = str(basic.get("shopid", ""))
                    name = str(basic.get("name", "")).strip()

                    # Shopee lưu giá nhân 100,000 (VND * 100000)
                    raw_price = basic.get("price", 0)
                    curr_price = float(raw_price) / 100000.0 if raw_price > 1000000 else float(raw_price)
                    orig_price_raw = basic.get("price_before_discount", 0)
                    orig_price = float(orig_price_raw) / 100000.0 if orig_price_raw > 1000000 else curr_price

                    if criteria:
                        if criteria.max_price and curr_price > criteria.max_price:
                            continue
                        if criteria.min_price and curr_price < criteria.min_price:
                            continue

                    rating = float(basic.get("item_rating", {}).get("rating_star", 5.0) or 5.0)
                    reviews_count = basic.get("historical_sold", 0)
                    image_id = basic.get("image", "")
                    thumb = f"https://down-vn.img.susercontent.com/file/{image_id}" if image_id else ""
                    is_mall = bool(basic.get("is_official_shop") or basic.get("show_official_shop_label"))

                    product_entry = {
                        "id": f"shopee-{item_id}",
                        "name": name,
                        "category": criteria.category if criteria else "all",
                        "categoryName": criteria.category_name if criteria else "Sản phẩm",
                        "platform": "shopee",
                        "platformName": "Shopee Mall" if is_mall else "Shopee",
                        "platformBadgeColor": "#ee4d2d",
                        "platformBadgeBg": "rgba(238, 77, 45, 0.15)",
                        "aiMatchScore": 95 if rating >= 4.5 else 85,
                        "originalPrice": orig_price,
                        "currentPrice": curr_price,
                        "discountPercent": int(basic.get("raw_discount", 0)),
                        "rating": rating,
                        "reviewsCount": f"{reviews_count} đã bán",
                        "sku": f"SHOPEE-{item_id}",
                        "image": thumb,
                        "aiSummary": f"Sản phẩm thực tế trên Shopee: {name}. Đánh giá {rating:.1f}/5 với {reviews_count} lượt bán.",
                        "warranty": "Chính hãng 100%" if is_mall else "Theo chính sách Shop",
                        "deliveryTag": "Shopee Xpress",
                        "selected": False,
                        "externalUrl": f"https://shopee.vn/product/{shop_id}/{item_id}"
                    }
                    shopee_products.append(product_entry)
                    if len(shopee_products) >= limit:
                        break
        except Exception as e:
            logger.warning(f"Lỗi khi tìm kiếm Shopee: {e}")

        return shopee_products

    async def _search_mwg(
        self,
        platform: str,
        search_keyword: str,
        criteria: Optional[UniversalSearchCriteria],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Cào dữ liệu sản phẩm thực tế từ hệ thống bán lẻ Thế Giới Di Động (tgdd) hoặc Điện Máy Xanh (dmx).
        Dữ liệu SSR có cấu trúc giàu thông tin, không yêu cầu captcha.
        """
        domain = "https://www.thegioididong.com" if platform == "tgdd" else "https://www.dienmayxanh.com"
        platform_name = "Thế Giới Di Động" if platform == "tgdd" else "Điện Máy Xanh"
        badge_color = "#ffd400" if platform == "tgdd" else "#0083d1"
        badge_bg = "rgba(255, 212, 0, 0.15)" if platform == "tgdd" else "rgba(0, 131, 209, 0.15)"
        warranty = "Chính hãng TGDĐ (1 đổi 1 tháng đầu)" if platform == "tgdd" else "Chính hãng ĐMX (Lắp đặt tận nhà)"
        delivery_tag = "Giao nhanh 2h" if platform == "tgdd" else "Giao hàng & Lắp đặt"

        mwg_products: List[Dict[str, Any]] = []
        try:
            encoded_q = urllib.parse.quote(search_keyword)
            search_url = f"{domain}/tim-kiem?key={encoded_q}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": f"{domain}/"
            }
            async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=8.0) as client:
                resp = await client.get(search_url)
                if resp.status_code == 200 and resp.text:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    items = soup.select("li.item[data-id]:not(.merge__item)")
                    for item in items:
                        a_tag = item.select_one("a.main-contain, a[href]")
                        if not a_tag:
                            continue

                        name = a_tag.get("data-name") or ""
                        if not name:
                            title_tag = item.select_one("h3, p.product-title")
                            if title_tag:
                                name = title_tag.get_text(strip=True)
                                name = re.sub(r'Mẫu mới|Hàng sắp về', '', name).strip()
                        if not name:
                            continue

                        raw_price_attr = item.get("data-price") or a_tag.get("data-price")
                        curr_price = 0.0
                        if raw_price_attr:
                            try:
                                curr_price = float(raw_price_attr)
                            except (ValueError, TypeError):
                                pass
                        if curr_price <= 0:
                            price_elem = item.select_one(".price, strong.price")
                            if price_elem:
                                cleaned = re.sub(r'[^\d]', '', price_elem.get_text())
                                if cleaned:
                                    curr_price = float(cleaned)
                        if curr_price <= 0:
                            continue

                        # Lọc giá theo criteria của người dùng
                        if criteria:
                            if criteria.max_price and curr_price > criteria.max_price:
                                continue
                            if criteria.min_price and curr_price < criteria.min_price:
                                continue

                        orig_price = curr_price
                        discount_pct = 0
                        old_price_elem = item.select_one(".price-old, .strike, box-p .price-old")
                        if old_price_elem:
                            cleaned_old = re.sub(r'[^\d]', '', old_price_elem.get_text())
                            if cleaned_old:
                                try:
                                    orig_price = float(cleaned_old)
                                except ValueError:
                                    orig_price = curr_price

                        percent_elem = item.select_one(".percent")
                        if percent_elem:
                            pct_m = re.search(r'(\d+)%', percent_elem.get_text())
                            if pct_m:
                                discount_pct = int(pct_m.group(1))
                        elif orig_price > curr_price:
                            discount_pct = int(round((1 - curr_price / orig_price) * 100))

                        href = a_tag.get("href", "")
                        if href and not href.startswith("http"):
                            href = f"{domain}{href}"

                        img_elem = item.select_one(".item-img img, img")
                        thumb = ""
                        if img_elem:
                            thumb = img_elem.get("src") or img_elem.get("data-src") or ""
                            if thumb.startswith("//"):
                                thumb = f"https:{thumb}"

                        rating = 5.0
                        vote_elem = item.select_one(".vote-txt b, .vote-txt")
                        if vote_elem:
                            try:
                                vote_val = float(re.sub(r'[^\d\.]', '', vote_elem.get_text()) or 5.0)
                                if 1.0 <= vote_val <= 5.0:
                                    rating = vote_val
                            except Exception:
                                rating = 5.0

                        reviews_count = "Chính hãng"
                        sold_elem = item.select_one(".rating_Compare span")
                        if sold_elem:
                            reviews_count = sold_elem.get_text(strip=True).lstrip("•").strip()

                        utility_p = [p.get_text(strip=True) for p in item.select(".utility p") if p.get_text(strip=True)]
                        specs_str = " - ".join(utility_p) if utility_p else ""
                        ai_summary = f"Sản phẩm thực tế tại {platform_name}: {name}. {specs_str}" if specs_str else f"Sản phẩm thực tế tại {platform_name}: {name}."

                        item_id = item.get("data-id") or ""

                        product_entry = {
                            "id": f"{platform}-{item_id}",
                            "name": name,
                            "category": criteria.category if criteria else "all",
                            "categoryName": criteria.category_name if criteria else "Sản phẩm",
                            "platform": platform,
                            "platformName": platform_name,
                            "platformBadgeColor": badge_color,
                            "platformBadgeBg": badge_bg,
                            "aiMatchScore": 95 if rating >= 4.5 else 85,
                            "originalPrice": orig_price,
                            "currentPrice": curr_price,
                            "discountPercent": discount_pct,
                            "rating": rating,
                            "reviewsCount": reviews_count,
                            "sku": f"{platform.upper()}-{item_id}",
                            "image": thumb,
                            "aiSummary": ai_summary,
                            "warranty": warranty,
                            "deliveryTag": delivery_tag,
                            "selected": False,
                            "externalUrl": href
                        }
                        mwg_products.append(product_entry)
                        if len(mwg_products) >= limit:
                            break
        except Exception as e:
            logger.warning(f"Lỗi khi tìm kiếm {platform_name}: {e}")

        return mwg_products

    async def run(
        self,
        query: str,
        category: str = "all",
        criteria: Optional[UniversalSearchCriteria] = None,
        platform: str = "all",
        limit: int = 6,
        force_refresh: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Thực hiện tìm kiếm sản phẩm thực tế từ các chuỗi bán lẻ: Tiki, Thế Giới Di Động, Điện Máy Xanh.
        Áp dụng cơ chế Cache-First (kiểm tra SQLite trước, chỉ cào mạng khi chưa có hoặc hết hạn).
        Không sử dụng dữ liệu giả lập (mock data).
        """
        search_keyword = criteria.cleaned_query if (criteria and criteria.cleaned_query) else query
        if not search_keyword.strip():
            return []

        # Xác định sàn mục tiêu
        effective_platform = platform.lower().strip() if (platform and platform != "all") else "all"
        if effective_platform == "all" and criteria and criteria.target_platforms:
            effective_platform = criteria.target_platforms[0].lower().strip()

        # =====================================================================
        # 1. KIỂM TRA BỘ NHỚ ĐỆM (CACHE-FIRST) TRƯỚC KHI CÀO MẠNG
        # =====================================================================
        if not force_refresh:
            try:
                cached_products = await product_repository.get_cached_search(
                    query=search_keyword,
                    platform=effective_platform
                )
                if cached_products:
                    # Áp dụng bộ lọc giá criteria nếu có
                    filtered_cached = []
                    for p in cached_products:
                        curr_p = float(p.get("currentPrice", 0))
                        if criteria:
                            if criteria.max_price and curr_p > criteria.max_price:
                                continue
                            if criteria.min_price and curr_p < criteria.min_price:
                                continue
                        filtered_cached.append(p)
                        if len(filtered_cached) >= limit:
                            break
                    if filtered_cached:
                        logger.info(
                            f"⚡ [Cache Hit] Trả về {len(filtered_cached)} sản phẩm từ SQLite cho '{search_keyword}' (platform={effective_platform}) trong <20ms"
                        )
                        return filtered_cached
            except Exception as cache_err:
                logger.warning(f"Lỗi kiểm tra cache SQLite: {cache_err}")

        # =====================================================================
        # 2. NẾU CHƯA CÓ TRONG CACHE -> CÀO MẠNG THỰC TẾ (CACHE MISS)
        # =====================================================================
        if platform and platform != "all":
            target_platforms = [platform.lower()]
        else:
            target_platforms = [p.lower() for p in (criteria.target_platforms or ["all"])] if criteria else ["all"]

        products: List[Dict[str, Any]] = []

        # Tạm thời tắt cào Lazada và Shopee theo yêu cầu
        should_search_lazada = False
        should_search_shopee = False

        # Quyết định sàn tìm kiếm dựa trên yêu cầu (Ưu tiên các nguồn ổn định: Tiki, TGDĐ, ĐMX)
        should_search_tiki = "all" in target_platforms or "tiki" in target_platforms
        should_search_tgdd = "all" in target_platforms or "tgdd" in target_platforms or "thegioididong" in target_platforms
        should_search_dmx = "all" in target_platforms or "dmx" in target_platforms or "dienmayxanh" in target_platforms

        if "lazada" in target_platforms or "shopee" in target_platforms:
            logger.info("ℹ️ Kênh Lazada và Shopee đang tạm thời dừng thu thập theo cấu hình.")

        tasks = []
        platform_order = []
        if should_search_tgdd:
            tasks.append(self._search_mwg("tgdd", search_keyword, criteria, limit=limit))
            platform_order.append("tgdd")
        if should_search_dmx:
            tasks.append(self._search_mwg("dmx", search_keyword, criteria, limit=limit))
            platform_order.append("dmx")
        if should_search_tiki:
            tasks.append(self._search_tiki(search_keyword, criteria, limit=limit))
            platform_order.append("tiki")

        results = await asyncio.gather(*tasks, return_exceptions=True)

        platform_results: Dict[str, List[Dict[str, Any]]] = {
            "tgdd": [],
            "dmx": [],
            "tiki": []
        }

        for idx, plat_name in enumerate(platform_order):
            res = results[idx]
            if isinstance(res, list):
                platform_results[plat_name] = res

        tgdd_res = platform_results["tgdd"]
        dmx_res = platform_results["dmx"]
        tiki_res = platform_results["tiki"]

        # Đan xen kết quả đa nguồn (TGDĐ, ĐMX, Tiki) để so sánh giá tối ưu
        active_lists = [l for l in [tgdd_res, dmx_res, tiki_res] if l]
        max_len = max([len(l) for l in active_lists]) if active_lists else 0

        for i in range(max_len):
            for l in active_lists:
                if i < len(l):
                    products.append(l[i])
                    if len(products) >= limit:
                        break
            if len(products) >= limit:
                break

        logger.info(
            f"🔍 Tìm kiếm thực tế cho '{search_keyword}': {len(tgdd_res)} TGDD, "
            f"{len(dmx_res)} DMX, {len(tiki_res)} Tiki -> Trả về: {len(products)} sản phẩm."
        )

        # =====================================================================
        # 3. TỰ ĐỘNG LƯU VÀO CSDL VÀ CẬP NHẬT CACHE CHO LẦN SAU
        # =====================================================================
        if products:
            try:
                await product_repository.save_search_cache(
                    query=search_keyword,
                    platform=effective_platform,
                    products=products,
                    ttl_hours=2  # Ghi nhớ trong vòng 2 tiếng
                )
            except Exception as save_err:
                logger.warning(f"Lỗi tự động lưu cache CSDL: {save_err}")

        return products



