"""Theo dõi giá: tạo / xóa yêu cầu, xem nhật ký kiểm tra, kiểm tra giá ngay.

Job kiểm tra định kỳ nằm ở jobs/price_watcher.py.
"""
import time
from typing import Any, Dict, List, Optional, Tuple

from database.models import UserModel
from database.repositories import alert_repository, price_check_repository, product_repository
from jobs.price_watcher import price_watcher_service
from services.catalog.categories import categorize
from services.pricing import guardrails as price_guardrails
from shared.exceptions import InvalidInputError, NotFoundError

MAX_CHECKS_PER_ALERT = 100
MAX_CHECKS_ADMIN = 500


async def _server_price(product: Dict[str, Any]) -> Tuple[Optional[float], Optional[bool]]:
    """(giá, còn hàng) do server xác định, không tin giá giao diện gửi lên (có thể cũ hoặc đọc nhầm khi cào).

    Đọc trực tiếp từ sàn; không được thì dùng giá đã lưu trong kho nếu qua guardrails.
    Còn hàng = None khi không đọc được trang.
    """
    live = await price_watcher_service.fetch_price(product) or {}
    stored = await product_repository.get_product_by_id(product["id"])
    category_path = live.get("sourceCategoryPath") or (stored or {}).get("sourceCategoryPath")
    category = categorize({**product, "sourceCategoryPath": category_path})
    in_stock = live.get("inStock")
    if price_guardrails.check_price(live.get("currentPrice"), category).ok:
        # Lần đọc thật -> ghi luôn mốc giá
        await product_repository.upsert_products([{**product, "currentPrice": live["currentPrice"],
                                                   "originalPrice": live.get("originalPrice") or live["currentPrice"]}])
        return float(live["currentPrice"]), in_stock
    if stored and price_guardrails.check_price(stored["currentPrice"], category).ok:
        return float(stored["currentPrice"]), in_stock
    return None, in_stock


async def create_alert(user: UserModel, product: Dict[str, Any], target_price: float) -> Dict[str, Any]:
    """Theo dõi giá một sản phẩm; giá mong muốn phải thấp hơn giá hiện tại trên sàn."""
    price, in_stock = await _server_price(product)
    if price is None:
        raise InvalidInputError("Chưa đọc được giá hiện tại của sản phẩm trên sàn, vui lòng thử lại sau.")
    if target_price >= price:
        raise InvalidInputError(f"Giá mong muốn phải thấp hơn giá hiện tại trên sàn ({price:,.0f} đ).".replace(",", "."))
    return await alert_repository.create({
        "id": f"alert-{int(time.time() * 1000)}",
        "product_id": product["id"],
        "product_name": product["name"],
        "product_url": product.get("externalUrl", ""),
        "image": product.get("image", ""),
        "platform": product["platform"],
        "platform_name": product.get("platformName", ""),
        "target_price": target_price,
        "initial_price": price,
        "last_price": price,
        "lowest_price": price,
        "status": "watching",
        "in_stock": in_stock,
        "user_id": user.id,
        "user_email": user.email,
    })


async def list_alerts(user: UserModel) -> List[Dict[str, Any]]:
    return await alert_repository.list(user_id=user.id)


async def delete_alert(user: UserModel, alert_id: str) -> Dict[str, Any]:
    if not await alert_repository.delete(alert_id, user_id=user.id):
        raise NotFoundError("Không tìm thấy yêu cầu theo dõi giá.")
    await price_check_repository.delete_for_alert(alert_id)
    return {"id": alert_id, "deleted": True}


async def list_checks(user: UserModel, alert_id: str, limit: int) -> List[Dict[str, Any]]:
    """Nhật ký các lần kiểm tra giá của một yêu cầu (chỉ chủ sở hữu)."""
    if not any(a["id"] == alert_id for a in await alert_repository.list(user_id=user.id)):
        raise NotFoundError("Không tìm thấy yêu cầu theo dõi giá.")
    return await price_check_repository.list(alert_id=alert_id, limit=min(limit, MAX_CHECKS_PER_ALERT))


async def check_now(user: UserModel, alert_ids: Optional[List[str]]) -> List[Dict[str, Any]]:
    """Kiểm tra giá ngay (đọc trang sản phẩm thật), không chờ chu kỳ nền; alert_ids None = mọi yêu cầu đang theo dõi."""
    return await price_watcher_service.check_alerts(alert_ids, user_id=user.id)


async def system_check_log(user_id: Optional[str], limit: int) -> List[Dict[str, Any]]:
    """Quản trị viên: nhật ký kiểm tra giá của toàn hệ thống, lọc được theo người dùng."""
    return await price_check_repository.list(user_id=user_id, limit=min(limit, MAX_CHECKS_ADMIN))
