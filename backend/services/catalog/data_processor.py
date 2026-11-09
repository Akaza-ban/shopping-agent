import logging
import re
import urllib.parse
from typing import Any

logger = logging.getLogger("data_processor")

PROMOTIONAL_PATTERNS = [
    r"\[.*?\]",
    r"\(chính hãng.*?\)",
    r"\(nhập khẩu.*?\)",
    r"\(đã kích hoạt.*?\)",
    r"\(bảo hành.*?\)",
    r"hàng chính hãng\s*(?:vn/a)?",
    r"chính hãng\s*vn/a",
    r"bảo hành\s*\d+\s*(?:tháng|t)",
    r"mẫu mới\s*(?:202\d)?",
    r"hàng sắp về",
    r"giá sốc",
    r"giảm sâu",
    r"tặng kèm quà.*?(?:$|-|,)",
    r"miễn phí vận chuyển",
    r"giao nhanh\s*\d+h",
]


def _to_number(val: Any) -> float:
    """ "15.990.000₫" / "19,490,000 VND" / 19490000 -> 19490000.0; không đọc được -> 0."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    cleaned = re.sub(r"[^\d]", "", str(val))
    return float(cleaned) if cleaned else 0.0


def _spec_label(part: str, filled: int) -> str:
    """Nhãn cho một đoạn thông số không có dạng "Nhãn: giá trị" (VD: "Chip A17 Pro" -> "Chip / CPU")."""
    if re.search(r'inch|"', part, re.IGNORECASE):
        return "Màn hình"
    if re.search(r"\b(?:apple a\d+|snapdragon|helio|dimensity|intel|ryzen|m\d)\b", part, re.IGNORECASE):
        return "Chip / CPU"
    if re.search(r"\d+\s*(?:gb|tb)\b", part, re.IGNORECASE):
        return "RAM" if "ram" in part.lower() else "Bộ nhớ / Ổ cứng"
    return f"Tính năng {filled + 1}"


class DataProcessor:
    def clean_title(self, raw_title: str) -> str:
        if not raw_title:
            return ""
        title = str(raw_title)

        # 1. Loại bỏ các mẫu quảng cáo thường gặp
        for pattern in PROMOTIONAL_PATTERNS:
            title = re.sub(pattern, " ", title, flags=re.IGNORECASE)

        title = re.sub(r"^[-\|:/\s]+|[-\|:/\s]+$", "", title)

        # 3. Chuẩn hóa khoảng trắng thừa, tab, xuống dòng
        title = re.sub(r"\s+", " ", title).strip()

        return title

    def normalize_price_and_discount(
        self, raw_current_price: Any, raw_original_price: Any, raw_discount: Any = None
    ) -> tuple[float, float, int]:
        """(giá bán, giá gốc, % giảm) dạng số sạch."""
        curr_price = _to_number(raw_current_price)
        orig_price = _to_number(raw_original_price)
        if orig_price <= 0 or orig_price < curr_price:
            orig_price = curr_price
        discount = int(round((1.0 - (curr_price / orig_price)) * 100)) if orig_price > curr_price else 0
        if raw_discount is not None:
            platform_discount = int(_to_number(raw_discount))
            if 0 <= platform_discount <= 100:
                discount = max(discount, platform_discount)
        return curr_price, orig_price, discount

    def clean_url_and_image(self, raw_url: str, raw_image: str) -> tuple[str, str]:
        clean_url = str(raw_url or "").strip()
        if clean_url:
            parsed = urllib.parse.urlparse(clean_url)
            # Chỉ giữ lại URL gốc không kèm query tracking
            clean_url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))

        clean_img = str(raw_image or "").strip()
        if clean_img.startswith("//"):
            clean_img = f"https:{clean_img}"

        return clean_url, clean_img

    def structure_specs(self, raw_specs: Any, product_name: str) -> dict[str, str]:
        """Thông số dạng {nhãn: giá trị} từ dict của sàn, hoặc từ chuỗi kiểu TGDĐ ("Màn hình 6.7" - Chip A17 Pro - RAM 8 GB");"""
        specs_dict: dict[str, str] = {}
        if isinstance(raw_specs, dict):
            for k, v in raw_specs.items():
                if k and v:
                    specs_dict[str(k).strip()] = str(v).strip()
        elif isinstance(raw_specs, str) and raw_specs.strip():
            for part in (p.strip() for p in re.split(r"[-|;]", raw_specs)):
                if not part:
                    continue
                if ":" in part:
                    k, v = part.split(":", 1)
                    specs_dict[k.strip()] = v.strip()
                else:
                    specs_dict[_spec_label(part, len(specs_dict))] = part

        storage_match = re.search(r"\b(\d+\s*(?:gb|tb))\b", product_name, re.IGNORECASE)
        if storage_match and "Bộ nhớ / Ổ cứng" not in specs_dict:
            specs_dict["Bộ nhớ / Ổ cứng"] = storage_match.group(1).upper()
        ram_match = re.search(r"\b(?:ram\s*)?(\d+)\s*gb\s*ram\b", product_name, re.IGNORECASE)
        if ram_match and "RAM" not in specs_dict:
            specs_dict["RAM"] = f"{ram_match.group(1)}GB"
        return specs_dict

    def extract_brand(self, product_name: str, existing_brand: str = "") -> str:
        """Lấy thương hiệu trực tiếp do sàn cung cấp (metadata chính thức)."""
        brand = str(existing_brand or "").strip()
        if brand and brand.lower() not in ("none", "chính hãng", "no brand", "oem", "khác", ""):
            return brand.title() if brand.islower() else brand

        return "Chính hãng"

    def normalize_rating_and_reviews(self, raw_rating: Any, raw_reviews: Any) -> tuple[float, str]:
        # Rating
        try:
            r = float(raw_rating or 0.0)
            clean_rating = round(min(5.0, max(1.0, r)), 1) if r > 0 else 0.0
        except (ValueError, TypeError):
            clean_rating = 0.0

        # Reviews count
        clean_reviews = str(raw_reviews or "Chưa có đánh giá").strip()
        if not clean_reviews or re.fullmatch(r"0\s*đánh giá", clean_reviews, re.IGNORECASE):
            clean_reviews = "Chưa có đánh giá"

        return clean_rating, clean_reviews

    def process_product(self, raw: dict[str, Any]) -> dict[str, Any] | None:
        raw_name = raw.get("name", "")
        clean_name = self.clean_title(raw_name)
        if not clean_name:
            return None

        # 1. Chuẩn hóa giá
        curr_price, orig_price, discount = self.normalize_price_and_discount(
            raw.get("currentPrice"), raw.get("originalPrice"), raw.get("discountPercent")
        )
        if curr_price <= 0:
            return None

        # 2. Chuẩn hóa link và ảnh
        clean_url, clean_image = self.clean_url_and_image(raw.get("externalUrl", ""), raw.get("image", ""))

        # 3. Cấu trúc hóa specs
        specs = self.structure_specs(raw.get("specs"), clean_name)

        # 4. Thương hiệu & Rating
        brand = self.extract_brand(clean_name, raw.get("brand", ""))
        rating, reviews_count = self.normalize_rating_and_reviews(raw.get("rating"), raw.get("reviewsCount"))

        # Tạo bản ghi sản phẩm chuẩn hóa hoàn chỉnh
        processed: dict[str, Any] = {
            "id": str(raw.get("id", "")),
            "name": clean_name,
            "category": raw.get("category", "all"),
            "categoryName": raw.get("categoryName", "Sản phẩm"),
            "platform": raw.get("platform", "tiki"),
            "platformName": raw.get("platformName", "Sàn TMĐT"),
            "platformBadgeColor": raw.get("platformBadgeColor", "#1a94ff"),
            "platformBadgeBg": raw.get("platformBadgeBg", "rgba(26, 148, 255, 0.15)"),
            "aiMatchScore": int(raw.get("aiMatchScore", 90)),
            "originalPrice": orig_price,
            "currentPrice": curr_price,
            "discountPercent": discount,
            "rating": rating,
            "reviewsCount": reviews_count,
            "sku": raw.get("sku", ""),
            "image": clean_image,
            "specs": specs,
            "brand": brand,
            "aiSummary": raw.get("aiSummary", f"{clean_name} - Giá: {curr_price:,.0f} đ"),
            # Không có dữ liệu thì để trống (Advisor nói "Chưa rõ"), không tự điền
            "warranty": raw.get("warranty") or None,
            "deliveryTag": raw.get("deliveryTag") or None,
            "selected": False,
            "externalUrl": clean_url,
        }
        # Mã danh mục của sàn (Tiki) — RAG dùng để chuẩn hóa danh mục
        if raw.get("sourceCategoryPath"):
            processed["sourceCategoryPath"] = raw["sourceCategoryPath"]
            processed["sourceCategoryName"] = raw.get("sourceCategoryName", "")

        return processed

    def process_product_list(self, raw_products: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Làm sạch danh sách sản phẩm, bỏ sản phẩm không hợp lệ và trùng lặp (theo link / id)."""
        processed_list = []
        seen_urls = set()

        for raw_item in raw_products:
            clean_item = self.process_product(raw_item)
            if not clean_item:
                continue

            # Chống trùng lặp theo URL hoặc ID
            item_url = clean_item.get("externalUrl", "")
            item_id = clean_item.get("id", "")
            dedup_key = item_url or item_id

            if dedup_key and dedup_key in seen_urls:
                continue

            seen_urls.add(dedup_key)
            processed_list.append(clean_item)

        logger.info(
            f"[DataProcessor] Đã xử lý & làm sạch: {len(raw_products)} raw items "
            f"-> {len(processed_list)} clean standardized products."
        )
        return processed_list


data_processor = DataProcessor()
