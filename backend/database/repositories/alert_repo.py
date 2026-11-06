import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, delete
from ..connection import async_session
from ..models import AlertModel, PriceCheckModel

logger = logging.getLogger("alert_repo")


def alert_to_dict(a: AlertModel) -> Dict[str, Any]:
    iso = lambda d: d.isoformat() if d else None
    return {
        "id": a.id,
        "productId": a.product_id,
        "productName": a.product_name,
        "productUrl": a.product_url or "",
        "image": a.image or "",
        "platform": a.platform,
        "platformName": a.platform_name or "",
        "targetPrice": a.target_price,
        "initialPrice": a.initial_price,
        "lastPrice": a.last_price,
        "lowestPrice": a.lowest_price,
        "status": a.status or "watching",
        "lastCheckedAt": iso(a.last_checked_at),
        "triggeredAt": iso(a.triggered_at),
        "lastNote": a.last_note or "",
        "pendingPrice": a.pending_price,
        "inStock": a.in_stock,
        "userId": a.user_id,
        "userEmail": a.user_email or "",
        "createdAt": iso(a.created_at),
    }


class AlertRepository:

    def __init__(self, session_factory=async_session):
        self.session_factory = session_factory

    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        async with self.session_factory() as session:
            alert = AlertModel(**data, created_at=datetime.utcnow())
            session.add(alert)
            await session.commit()
            return alert_to_dict(alert)

    async def list(self, status: Optional[str] = None, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        async with self.session_factory() as session:
            stmt = select(AlertModel).order_by(AlertModel.created_at.desc())
            if status:
                stmt = stmt.where(AlertModel.status == status)
            if user_id:
                stmt = stmt.where(AlertModel.user_id == user_id)
            res = await session.execute(stmt)
            return [alert_to_dict(a) for a in res.scalars().all()]

    async def delete(self, alert_id: str, user_id: Optional[str] = None) -> bool:
        async with self.session_factory() as session:
            stmt = delete(AlertModel).where(AlertModel.id == alert_id)
            if user_id:
                stmt = stmt.where(AlertModel.user_id == user_id)
            res = await session.execute(stmt)
            await session.commit()
            return (res.rowcount or 0) > 0

    async def update(self, alert_id: str, **fields: Any) -> Optional[Dict[str, Any]]:
        async with self.session_factory() as session:
            alert = await session.get(AlertModel, alert_id)
            if not alert:
                return None
            for key, value in fields.items():
                setattr(alert, key, value)
            await session.commit()
            return alert_to_dict(alert)


def check_to_dict(c: PriceCheckModel) -> Dict[str, Any]:
    return {
        "id": c.id,
        "alertId": c.alert_id,
        "userId": c.user_id,
        "productName": c.product_name or "",
        "price": c.price,
        "inStock": c.in_stock,
        "outcome": c.outcome,
        "note": c.note or "",
        "latencyMs": c.latency_ms,
        "checkedAt": c.checked_at.isoformat() if c.checked_at else None,
    }


class PriceCheckRepository:

    def __init__(self, session_factory=async_session, keep_per_alert: int = 100):
        self.session_factory = session_factory
        self.keep_per_alert = keep_per_alert

    async def add(self, record: Dict[str, Any]) -> Dict[str, Any]:
        async with self.session_factory() as session:
            check = PriceCheckModel(**record)
            session.add(check)
            await session.flush()
            old_ids = (await session.execute(
                select(PriceCheckModel.id)
                .where(PriceCheckModel.alert_id == record["alert_id"])
                .order_by(PriceCheckModel.id.desc())
                .offset(self.keep_per_alert)
            )).scalars().all()
            if old_ids:
                await session.execute(delete(PriceCheckModel).where(PriceCheckModel.id.in_(old_ids)))
            await session.commit()
            return check_to_dict(check)

    async def list(self, user_id: Optional[str] = None, alert_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        async with self.session_factory() as session:
            q = select(PriceCheckModel).order_by(PriceCheckModel.id.desc()).limit(limit)
            if user_id:
                q = q.where(PriceCheckModel.user_id == user_id)
            if alert_id:
                q = q.where(PriceCheckModel.alert_id == alert_id)
            return [check_to_dict(c) for c in (await session.execute(q)).scalars().all()]

    async def delete_for_alert(self, alert_id: str) -> None:
        async with self.session_factory() as session:
            await session.execute(delete(PriceCheckModel).where(PriceCheckModel.alert_id == alert_id))
            await session.commit()


alert_repository = AlertRepository()
price_check_repository = PriceCheckRepository()
