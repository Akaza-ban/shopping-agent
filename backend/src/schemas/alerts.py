"""Dữ liệu vào của API theo dõi giá."""

from pydantic import BaseModel, Field


class AlertProduct(BaseModel):
    id: str
    name: str
    platform: str
    platformName: str = ""
    currentPrice: float
    originalPrice: float | None = None
    externalUrl: str = ""
    image: str = ""


class CreateAlertRequest(BaseModel):
    product: AlertProduct
    target_price: float = Field(gt=0, description="Báo khi giá bán <= mức này (VND)")


class CheckAlertsRequest(BaseModel):
    alert_ids: list[str] | None = None  # None = kiểm tra mọi yêu cầu đang theo dõi
