import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from ..connection import async_session
from ..models import ProductModel, PriceHistoryModel, SearchCacheModel

logger = logging.getLogger("product_repo")

def product_model_to_dict(model: ProductModel) -> Dict[str, Any]:
    """Chuyển đổi ORM Model sang Dictionary tương thích với giao diện và Agent."""
    badge_colors = {
        "tgdd": ("#ffd400", "rgba(255, 212, 0, 0.15)"),
        "dmx": ("#0083d1", "rgba(0, 131, 209, 0.15)"),
        "tiki": ("#1a94ff", "rgba(26, 148, 255, 0.15)"),
        "shopee": ("#ee4d2d", "rgba(238, 77, 45, 0.15)"),
        "lazada": ("#0f156d", "rgba(15, 21, 109, 0.15)")
    }
    badge_color, badge_bg = badge_colors.get(
        model.platform,
        ("#1a94ff", "rgba(26, 148, 255, 0.15)")
    )
    
    sku_suffix = model.id.split("-")[-1] if "-" in model.id else model.id

    return {
        "id": model.id,
        "name": model.name,
        "category": model.category,
        "categoryName": model.category_name,
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
        "specs": model.specs or "",
        "aiSummary": model.ai_summary or f"Sản phẩm thực tế tại {model.platform_name}: {model.name}.",
        "warranty": model.warranty or "Theo chính sách gian hàng",
        "deliveryTag": model.delivery_tag or "Giao hàng tiêu chuẩn",
        "selected": False,
        "externalUrl": model.external_url,
        "updatedAt": model.updated_at.isoformat() if model.updated_at else None
    }

class ProductRepository:
    """Repository quản lý lưu trữ, truy xuất và theo dõi lịch sử giá của sản phẩm."""

    def __init__(self, session_factory=async_session):
        self.session_factory = session_factory

    async def upsert_products(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Tự động nạp hoặc cập nhật danh sách sản phẩm vào CSDL.
        Nếu phát hiện giá thay đổi, tự động ghi nhận mốc mới vào price_history.
        """
        if not products:
            return []

        saved_products: List[Dict[str, Any]] = []

        async with self.session_factory() as session:
            for item in products:
                prod_id = str(item.get("id", "")).strip()
                if not prod_id:
                    continue

                curr_price = float(item.get("currentPrice") or item.get("current_price") or 0.0)
                orig_price = float(item.get("originalPrice") or item.get("original_price") or curr_price)
                disc_pct = int(item.get("discountPercent") or item.get("discount_percent") or 0)
                
                # Kiểm tra sản phẩm đã có trong DB chưa
                existing = await session.get(ProductModel, prod_id)

                if existing is None:
                    # 1. Thêm mới hoàn toàn
                    new_product = ProductModel(
                        id=prod_id,
                        name=str(item.get("name", "")).strip(),
                        category=item.get("category", "all"),
                        category_name=item.get("categoryName") or item.get("category_name", "Sản phẩm"),
                        platform=item.get("platform", "other"),
                        platform_name=item.get("platformName") or item.get("platform_name", "Cửa hàng"),
                        original_price=orig_price,
                        current_price=curr_price,
                        discount_percent=disc_pct,
                        rating=float(item.get("rating") or 5.0),
                        reviews_count=str(item.get("reviewsCount") or item.get("reviews_count") or "Chính hãng"),
                        image=item.get("image", ""),
                        specs=item.get("specs", ""),
                        ai_summary=item.get("aiSummary") or item.get("ai_summary", ""),
                        warranty=item.get("warranty", "Chính hãng"),
                        delivery_tag=item.get("deliveryTag") or item.get("delivery_tag", "Giao nhanh"),
                        external_url=item.get("externalUrl") or item.get("external_url", ""),
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    session.add(new_product)

                    # Ghi mốc lịch sử giá ban đầu
                    price_entry = PriceHistoryModel(
                        product_id=prod_id,
                        price=curr_price,
                        original_price=orig_price,
                        discount_percent=disc_pct,
                        recorded_at=datetime.utcnow()
                    )
                    session.add(price_entry)
                    saved_products.append(product_model_to_dict(new_product))

                else:
                    # 2. Cập nhật sản phẩm đã có
                    price_has_changed = abs(existing.current_price - curr_price) >= 1.0

                    if price_has_changed:
                        # Ghi nhận biến động giá vào bảng price_history
                        price_entry = PriceHistoryModel(
                            product_id=prod_id,
                            price=curr_price,
                            original_price=orig_price,
                            discount_percent=disc_pct,
                            recorded_at=datetime.utcnow()
                        )
                        session.add(price_entry)
                        logger.info(
                            f"📈 Ghi nhận biến động giá cho '{existing.name}': "
                            f"{existing.current_price:,.0f}đ -> {curr_price:,.0f}đ"
                        )

                    # Cập nhật thông tin mới nhất
                    existing.current_price = curr_price
                    existing.original_price = orig_price
                    existing.discount_percent = disc_pct
                    if item.get("rating"):
                        existing.rating = float(item["rating"])
                    if item.get("reviewsCount") or item.get("reviews_count"):
                        existing.reviews_count = str(item.get("reviewsCount") or item.get("reviews_count"))
                    if item.get("specs"):
                        existing.specs = item["specs"]
                    if item.get("image"):
                        existing.image = item["image"]
                    if item.get("externalUrl") or item.get("external_url"):
                        existing.external_url = item.get("externalUrl") or item.get("external_url")
                    existing.updated_at = datetime.utcnow()

                    saved_products.append(product_model_to_dict(existing))

            await session.commit()

        return saved_products

    async def get_cached_search(
        self,
        query: str,
        platform: str = "all"
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Kiểm tra xem từ khóa này đã có kết quả cache trong DB và còn hạn sử dụng hay không.
        Trả về None nếu cache không tồn tại hoặc đã hết hạn.
        """
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
            except Exception:
                return None

            if not product_ids:
                return None

            # Lấy sản phẩm từ database theo danh sách IDs đã lưu trong cache
            prod_stmt = select(ProductModel).where(ProductModel.id.in_(product_ids))
            prod_res = await session.execute(prod_stmt)
            products_map = {p.id: product_model_to_dict(p) for p in prod_res.scalars().all()}

            # Giữ nguyên thứ tự ID ban đầu
            ordered_products = [products_map[pid] for pid in product_ids if pid in products_map]
            
            if ordered_products:
                logger.info(f"⚡ Cache Hit: Trả về {len(ordered_products)} sản phẩm cho '{clean_q}' ({clean_plat})")
                return ordered_products

        return None

    async def save_search_cache(
        self,
        query: str,
        platform: str,
        products: List[Dict[str, Any]],
        ttl_hours: int = 2
    ) -> None:
        """
        Lưu danh sách sản phẩm và ghi nhận từ khóa vào bảng search_cache với thời gian hết hạn TTL.
        """
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
            logger.info(f"💾 Đã lưu cache tìm kiếm cho '{clean_q}' ({clean_plat}) - Hết hạn trong {ttl_hours}h")

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

# Singleton instance sẵn sàng dùng trong toàn ứng dụng
product_repository = ProductRepository()
