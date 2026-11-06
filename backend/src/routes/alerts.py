import time
from typing import List, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from database.repositories import alert_repository, price_check_repository, product_repository
from services.pricing import guardrails as price_guardrails
from services.catalog.categories import categorize
from services.pricing.watcher import price_watcher_service
from database.models import UserModel
from src.auth import require_user, require_admin

router = APIRouter(prefix="/alerts", tags=["Price Alerts"])


class AlertProduct(BaseModel):
    id: str
    name: str
    platform: str
    platformName: str = ""
    currentPrice: float
    originalPrice: Optional[float] = None
    externalUrl: str = ""
    image: str = ""


class CreateAlertRequest(BaseModel):
    product: AlertProduct
    target_price: float = Field(gt=0, description="Báo khi giá bán <= mức này (VND)")


class CheckAlertsRequest(BaseModel):
    alert_ids: Optional[List[str]] = None  # None = kiểm tra mọi yêu cầu đang theo dõi


async def _server_price(p: AlertProduct) -> Tuple[Optional[float], Optional[bool]]:
    """Giá gốc của yêu cầu theo dõi do server xác định, không tin giá giao diện gửi lên (có thể cũ hoặc là giá đọc nhầm khi cào): đọc trực tiếp từ sàn; không được thì dùng giá đã lưu trong kho nếu qua guardrails. Trả về (giá, còn hàng); còn hàng = None khi không đọc được trang."""
    live = await price_watcher_service.fetch_price(p.model_dump()) or {}
    stored = await product_repository.get_product_by_id(p.id)
    category_path = live.get("sourceCategoryPath") or (stored or {}).get("sourceCategoryPath")
    category = categorize({**p.model_dump(), "sourceCategoryPath": category_path})
    in_stock = live.get("inStock")
    if price_guardrails.check_price(live.get("currentPrice"), category).ok:
        # Lần đọc thật -> ghi luôn mốc giá
        await product_repository.upsert_products([{**p.model_dump(), "currentPrice": live["currentPrice"],
                                                   "originalPrice": live.get("originalPrice") or live["currentPrice"]}])
        return float(live["currentPrice"]), in_stock
    if stored and price_guardrails.check_price(stored["currentPrice"], category).ok:
        return float(stored["currentPrice"]), in_stock
    return None, in_stock


@router.post("")
async def create_price_alert(req: CreateAlertRequest, user: UserModel = Depends(require_user)):
    """Theo dõi giá một sản phẩm; hệ thống kiểm tra định kỳ và đánh dấu khi giá xuống tới mức mong muốn."""
    p = req.product
    price, in_stock = await _server_price(p)
    if price is None:
        raise HTTPException(status_code=400, detail="Chưa đọc được giá hiện tại của sản phẩm trên sàn, vui lòng thử lại sau.")
    if req.target_price >= price:
        raise HTTPException(
            status_code=400,
            detail=f"Giá mong muốn phải thấp hơn giá hiện tại trên sàn ({price:,.0f} đ).".replace(",", "."),
        )
    return await alert_repository.create({
        "id": f"alert-{int(time.time() * 1000)}",
        "product_id": p.id,
        "product_name": p.name,
        "product_url": p.externalUrl,
        "image": p.image,
        "platform": p.platform,
        "platform_name": p.platformName,
        "target_price": req.target_price,
        "initial_price": price,
        "last_price": price,
        "lowest_price": price,
        "status": "watching",
        "in_stock": in_stock,
        "user_id": user.id,
        "user_email": user.email,
    })


@router.get("")
async def list_price_alerts(user: UserModel = Depends(require_user)):
    return await alert_repository.list(user_id=user.id)


@router.delete("/{alert_id}")
async def delete_price_alert(alert_id: str, user: UserModel = Depends(require_user)):
    if not await alert_repository.delete(alert_id, user_id=user.id):
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu theo dõi giá.")
    await price_check_repository.delete_for_alert(alert_id)
    return {"id": alert_id, "deleted": True}


@router.get("/{alert_id}/checks")
async def list_alert_checks(alert_id: str, limit: int = 20, user: UserModel = Depends(require_user)):
    """Nhật ký các lần kiểm tra giá của một yêu cầu (chỉ chủ sở hữu)."""
    if not any(a["id"] == alert_id for a in await alert_repository.list(user_id=user.id)):
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu theo dõi giá.")
    return await price_check_repository.list(alert_id=alert_id, limit=min(limit, 100))


@router.post("/check")
async def check_price_alerts(req: Optional[CheckAlertsRequest] = None, user: UserModel = Depends(require_user)):
    """Kiểm tra giá ngay (đọc trang sản phẩm thật) các yêu cầu của người dùng, không chờ chu kỳ nền."""
    return await price_watcher_service.check_alerts((req.alert_ids if req else None), user_id=user.id)


@router.get("/metrics", tags=["Price Alerts"])
async def get_price_check_log(user_id: Optional[str] = None, limit: int = 50, user: UserModel = Depends(require_admin)):
    """Nhật ký kiểm tra giá của toàn hệ thống (quản trị viên), lọc được theo người dùng."""
    return await price_check_repository.list(user_id=user_id, limit=min(limit, 500))
