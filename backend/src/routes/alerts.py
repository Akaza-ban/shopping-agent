from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import time
from services.price_watcher import PriceWatcherService

router = APIRouter(prefix="/alerts", tags=["Price Alerts"])
price_watcher = PriceWatcherService()

class PriceAlertItem(BaseModel):
    id: str
    product_name: str
    target_price: float
    platform: str
    user_email: str
    created_at: str

_ALERTS_DB: List[PriceAlertItem] = []

class CreateAlertRequest(BaseModel):
    product_name: str
    target_price: float
    platform: str
    user_email: str

@router.post("", response_model=PriceAlertItem)
async def create_price_alert(req: CreateAlertRequest):
    new_alert = PriceAlertItem(
        id=f"alert-{int(time.time() * 1000)}",
        product_name=req.product_name,
        target_price=req.target_price,
        platform=req.platform,
        user_email=req.user_email,
        created_at="Vừa xong"
    )
    _ALERTS_DB.append(new_alert)
    return new_alert

@router.get("", response_model=List[PriceAlertItem])
async def list_price_alerts():
    return _ALERTS_DB

@router.get("/metrics", tags=["Price Alerts"])
async def get_benchmark_metrics():
    """Truy xuất nhật ký Benchmark Guardrails."""
    return price_watcher.get_audit_metrics()
