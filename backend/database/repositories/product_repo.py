import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..connection import async_session
from ..errors import raises_database_error
from ..models import ProductModel, PriceHistoryModel, SearchCacheModel
from integrations.platforms import get_platform
# Ngoại lệ có chủ đích của hướng phụ thuộc: ngành hàng lưu trong CSDL tính theo bảng quy đổi danh mục đã học
from services.catalog.categories import categorize
from shared.product_key import product_key

logger = logging.getLogger("product_repo")

def product_model_to_dict(model: ProductModel) -> Dict[str, Any]:
    """Chuyển đổi ORM Model sang Dictionary tương thích với giao diện và Agent."""
    platform = get_platform(model.platform)
    badge_color, badge_bg = (platform.badge_color, platform.badge_bg) if platform else ("#1a94ff", "rgba(26, 148, 255, 0.15)")
    
    sku_suffix = model.id.split("-")[-1] if "-" in model.id else model.id

    return {
        "id": model.id,
        "name": model.name,
        "category": model.category,
        "categoryName": model.category_name,
        "sourceCategoryPath": model.source_category_path,
        "platform": model.platform,
        "platformName": model.platform_name,
        "platformBadgeColor": badge_color,
        "platformBadgeBg": badge_bg,
        "aiMatchScore": 95 if model.rating >= 4.5 else 85,
        "originalPrice": model.original_price,
        "currentPrice": model.current_price,
        "discountPercent": model.discount_percent,
        "rating": model.rating,
        "reviewsCount": model.reviews_count,
        "sku": f"{model.platform.upper()}-{sku_suffix}",
        "image": model.image,
        "specs": (json.loads(model.specs) if model.specs and model.specs.startswith("{") else (model.specs or "")),
        "aiSummary": model.ai_summary or f"Sản phẩm thực tế tại {model.platform_name}: {model.name}.",
        "warranty": model.warranty or "Theo chính sách gian hàng",
        "deliveryTag": model.delivery_tag or "Giao hàng tiêu chuẩn",
        "selected": False,
        "externalUrl": model.external_url,
        "updatedAt": model.updated_at.isoformat() if model.updated_at else None
    }


def _field(item: Dict[str, Any], camel: str, snake: str, default: Any = None) -> Any:
    """Giá trị theo tên khóa của giao diện (camelCase) hoặc của CSDL (snake_case)."""
    return item.get(camel) or item.get(snake, default)


def _prices(item: Dict[str, Any]) -> Tuple[float, float, int]:
    """(giá bán, giá gốc, % giảm); thiếu giá gốc thì lấy bằng giá bán."""
    current = float(_field(item, "currentPrice", "current_price") or 0.0)
    original = float(_field(item, "originalPrice", "original_price") or current)
    return current, original, int(_field(item, "discountPercent", "discount_percent") or 0)


def _specs_text(item: Dict[str, Any]) -> str:
    raw = item.get("specs")
    return json.dumps(raw, ensure_ascii=False) if isinstance(raw, dict) else str(raw or "")


def _price_point(prod_id: str, prices: Tuple[float, float, int]) -> PriceHistoryModel:
    current, original, discount = prices
    return PriceHistoryModel(product_id=prod_id, price=current, original_price=original,
                             discount_percent=discount, recorded_at=datetime.utcnow())


def _new_product(prod_id: str, item: Dict[str, Any], prices: Tuple[float, float, int]) -> ProductModel:
    current, original, discount = prices
    now = datetime.utcnow()
    return ProductModel(
        id=prod_id,
        name=str(item.get("name", "")).strip(),
        category=categorize(item),
        source_category_path=item.get("sourceCategoryPath"),
        category_name=_field(item, "categoryName", "category_name", "Sản phẩm"),
        platform=item.get("platform", "other"),
        platform_name=_field(item, "platformName", "platform_name", "Cửa hàng"),
        original_price=original,
        current_price=current,
        discount_percent=discount,
        rating=float(item.get("rating") or 0.0),  # 0 = chưa có đánh giá
        reviews_count=str(_field(item, "reviewsCount", "reviews_count") or "Chính hãng"),
        image=item.get("image", ""),
        specs=_specs_text(item),
        ai_summary=_field(item, "aiSummary", "ai_summary", ""),
        warranty=item.get("warranty", "Chính hãng"),
        delivery_tag=_field(item, "deliveryTag", "delivery_tag", "Giao nhanh"),
        external_url=_field(item, "externalUrl", "external_url", ""),
        created_at=now,
        updated_at=now,
    )


def _update_product(existing: ProductModel, item: Dict[str, Any], prices: Tuple[float, float, int]) -> None:
    """Ghi đè giá; các trường khác chỉ ghi khi lần cào này có dữ liệu (không xóa dữ liệu cũ bằng giá trị rỗng)."""
    existing.current_price, existing.original_price, existing.discount_percent = prices
    if item.get("rating"):
        existing.rating = float(item["rating"])
    if _field(item, "reviewsCount", "reviews_count"):
        existing.reviews_count = str(_field(item, "reviewsCount", "reviews_count"))
    if item.get("specs"):
        existing.specs = _specs_text(item)
    if item.get("image"):
        existing.image = item["image"]
    if _field(item, "externalUrl", "external_url"):
        existing.external_url = _field(item, "externalUrl", "external_url")
    if item.get("sourceCategoryPath"):
        existing.source_category_path = item["sourceCategoryPath"]
    existing.category = categorize({"sourceCategoryPath": existing.source_category_path,
                                    "externalUrl": existing.external_url})
    existing.updated_at = datetime.utcnow()


@raises_database_error
class ProductRepository:
    """Repository quản lý lưu trữ, truy xuất và theo dõi lịch sử giá của sản phẩm."""

    def __init__(self, session_factory=async_session):
        self.session_factory = session_factory

    async def catalog_snapshot(self) -> Tuple[int, Optional[datetime]]:
        """(số sản phẩm trong kho, thời điểm cập nhật gần nhất)."""
        async with self.session_factory() as session:
            total = (await session.execute(select(func.count()).select_from(ProductModel))).scalar() or 0
            latest = (await session.execute(
                select(ProductModel.updated_at).order_by(ProductModel.updated_at.desc()).limit(1)
            )).scalar_one_or_none()
        return total, latest

    async def category_prices(self) -> List[Tuple[str, float]]:
        """(ngành hàng, giá hiện tại) của mọi sản phẩm trong kho."""
        async with self.session_factory() as session:
            rows = (await session.execute(select(ProductModel.category, ProductModel.current_price))).all()
        return [(category, price) for category, price in rows]

    async def upsert_products(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Thêm mới hoặc cập nhật sản phẩm; giá đổi thì ghi thêm một mốc vào price_history."""
        saved: List[Dict[str, Any]] = []
        async with self.session_factory() as session:
            for item in products or []:
                prod_id = str(item.get("id", "")).strip()
                if not prod_id:
                    continue
                prices = _prices(item)
                existing = await session.get(ProductModel, prod_id)
                if existing is None:
                    model = _new_product(prod_id, item, prices)
                    session.add(model)
                    session.add(_price_point(prod_id, prices))  # mốc giá ban đầu
                else:
                    model = existing
                    if abs(existing.current_price - prices[0]) >= 1.0:
                        session.add(_price_point(prod_id, prices))
                        logger.info(f"Ghi nhận biến động giá cho '{existing.name}': "
                                    f"{existing.current_price:,.0f}đ -> {prices[0]:,.0f}đ")
                    _update_product(existing, item, prices)
                saved.append(product_model_to_dict(model))
            await session.commit()
        return saved

    async def get_cached_search(
        self,
        query: str,
        platform: str = "all"
    ) -> Optional[List[Dict[str, Any]]]:
        """Kiểm tra xem từ khóa này đã có kết quả cache trong DB và còn hạn sử dụng hay không."""
        clean_q = query.lower().strip()
        clean_plat = platform.lower().strip()

        async with self.session_factory() as session:
            stmt = (
                select(SearchCacheModel)
                .where(
                    SearchCacheModel.query == clean_q,
                    SearchCacheModel.platform == clean_plat,
                    SearchCacheModel.expires_at > datetime.utcnow()
                )
                .order_by(SearchCacheModel.created_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            cache_entry = result.scalar_one_or_none()

            if not cache_entry:
                return None

            try:
                product_ids: List[str] = json.loads(cache_entry.product_ids)
            except (ValueError, TypeError):
                return None

            if not product_ids:
                return None

            prod_stmt = select(ProductModel).where(ProductModel.id.in_(product_ids))
            prod_res = await session.execute(prod_stmt)
            products_map = {p.id: product_model_to_dict(p) for p in prod_res.scalars().all()}

            # Giữ nguyên thứ tự ID ban đầu
            ordered_products = [products_map[pid] for pid in product_ids if pid in products_map]
            
            if ordered_products:
                logger.info(f"Cache Hit: Trả về {len(ordered_products)} sản phẩm cho '{clean_q}' ({clean_plat})")
                return ordered_products

        return None

    async def save_search_cache(
        self,
        query: str,
        platform: str,
        products: List[Dict[str, Any]],
        ttl_hours: int = 2
    ) -> None:
        """Lưu danh sách sản phẩm và ghi nhận từ khóa vào bảng search_cache với thời gian hết hạn TTL."""
        if not products:
            return

        clean_q = query.lower().strip()
        clean_plat = platform.lower().strip()

        # 1. Lưu/cập nhật sản phẩm vào bảng products trước
        await self.upsert_products(products)

        product_ids = [p["id"] for p in products if "id" in p]
        expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)

        async with self.session_factory() as session:
            # Xóa cache cũ của cùng cặp (query, platform)
            await session.execute(
                delete(SearchCacheModel).where(
                    SearchCacheModel.query == clean_q,
                    SearchCacheModel.platform == clean_plat
                )
            )
            # Thêm cache mới
            new_cache = SearchCacheModel(
                query=clean_q,
                platform=clean_plat,
                product_ids=json.dumps(product_ids, ensure_ascii=False),
                created_at=datetime.utcnow(),
                expires_at=expires_at
            )
            session.add(new_cache)
            await session.commit()
            logger.info(f"Đã lưu cache tìm kiếm cho '{clean_q}' ({clean_plat}) - Hết hạn trong {ttl_hours}h")

    async def get_price_history(self, product_id: str) -> List[Dict[str, Any]]:
        """Lấy toàn bộ lịch sử biến động giá của một sản phẩm."""
        async with self.session_factory() as session:
            stmt = (
                select(PriceHistoryModel)
                .where(PriceHistoryModel.product_id == product_id)
                .order_by(PriceHistoryModel.recorded_at.asc())
            )
            res = await session.execute(stmt)
            history = res.scalars().all()
            return [
                {
                    "id": h.id,
                    "productId": h.product_id,
                    "price": h.price,
                    "originalPrice": h.original_price,
                    "discountPercent": h.discount_percent,
                    "recordedAt": h.recorded_at.isoformat()
                }
                for h in history
            ]

    async def get_product_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Lấy chi tiết một sản phẩm theo ID."""
        async with self.session_factory() as session:
            prod = await session.get(ProductModel, product_id)
            if prod:
                return product_model_to_dict(prod)
        return None

    async def get_reference_prices(self, names: List[str]) -> Dict[str, List[float]]:
        """Giá đã lưu của các bản ghi cùng tên, theo khóa `guardrails.product_key` (để phát hiện giá bất thường)."""
        names = list({n for n in names if n})
        if not names:
            return {}
        async with self.session_factory() as session:
            rows = await session.execute(
                select(ProductModel.name, ProductModel.current_price).where(ProductModel.name.in_(names))
            )
            refs: Dict[str, List[float]] = {}
            for name, price in rows.all():
                if price:
                    refs.setdefault(product_key(name), []).append(float(price))
            return refs

    async def find_by_name_terms(self, terms: List[str], limit: int = 300) -> List[Dict[str, Any]]:
        """Sản phẩm có tên chứa đủ mọi từ khóa (không phân biệt hoa thường): id, tên, sàn, giá."""
        terms = [t.lower() for t in terms if t]
        if not terms:
            return []
        anchor = max(terms, key=len)
        async with self.session_factory() as session:
            rows = await session.execute(
                select(ProductModel.id, ProductModel.name, ProductModel.platform, ProductModel.current_price)
                .where(ProductModel.name.ilike(f"%{anchor}%")).limit(limit))
            return [{"id": pid, "name": name, "platform": platform, "currentPrice": price}
                    for pid, name, platform, price in rows.all()
                    if all(t in (name or "").lower() for t in terms)]

    async def delete_products(self, product_ids: List[str]) -> int:
        """Xóa sản phẩm cùng lịch sử giá của chúng (SQLite không tự cascade khi chưa bật foreign_keys)."""
        if not product_ids:
            return 0
        async with self.session_factory() as session:
            await session.execute(delete(PriceHistoryModel).where(PriceHistoryModel.product_id.in_(product_ids)))
            res = await session.execute(delete(ProductModel).where(ProductModel.id.in_(product_ids)))
            await session.commit()
            return res.rowcount or 0

# Singleton instance sẵn sàng dùng trong toàn ứng dụng
product_repository = ProductRepository()
