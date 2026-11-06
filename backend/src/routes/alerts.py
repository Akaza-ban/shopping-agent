"""API theo dõi giá. Logic nằm ở application/alerts.py."""
from typing import Optional

from fastapi import APIRouter, Depends

import application.alerts as alerts
from database.models import UserModel
from src.dependencies.auth import require_admin, require_user
from src.schemas.alerts import CheckAlertsRequest, CreateAlertRequest

router = APIRouter(prefix="/alerts", tags=["Price Alerts"])


@router.post("")
async def create_price_alert(req: CreateAlertRequest, user: UserModel = Depends(require_user)):
    """Theo dõi giá một sản phẩm; hệ thống kiểm tra định kỳ và đánh dấu khi giá xuống tới mức mong muốn."""
    return await alerts.create_alert(user, req.product.model_dump(), req.target_price)


@router.get("")
async def list_price_alerts(user: UserModel = Depends(require_user)):
    return await alerts.list_alerts(user)


@router.delete("/{alert_id}")
async def delete_price_alert(alert_id: str, user: UserModel = Depends(require_user)):
    return await alerts.delete_alert(user, alert_id)


@router.get("/{alert_id}/checks")
async def list_alert_checks(alert_id: str, limit: int = 20, user: UserModel = Depends(require_user)):
    """Nhật ký các lần kiểm tra giá của một yêu cầu (chỉ chủ sở hữu)."""
    return await alerts.list_checks(user, alert_id, limit)


@router.post("/check")
async def check_price_alerts(req: Optional[CheckAlertsRequest] = None, user: UserModel = Depends(require_user)):
    """Kiểm tra giá ngay các yêu cầu của người dùng, không chờ chu kỳ nền."""
    return await alerts.check_now(user, req.alert_ids if req else None)


@router.get("/metrics", tags=["Price Alerts"])
async def get_price_check_log(user_id: Optional[str] = None, limit: int = 50, user: UserModel = Depends(require_admin)):
    """Nhật ký kiểm tra giá của toàn hệ thống (quản trị viên), lọc được theo người dùng."""
    return await alerts.system_check_log(user_id, limit)
