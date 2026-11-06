import asyncio
import time
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from services.pricing import guardrails
from services.catalog.categories import categorize
from services.catalog.category_resolver import category_resolver
from services.pricing.category_floors import category_floors
from services.catalog.enricher import product_enricher
from database.repositories import alert_repository, product_repository, price_check_repository

logger = logging.getLogger("price_watcher")


def _vnd(x: float) -> str:
    return f"{x:,.0f} đ".replace(",", ".")


class PriceWatcherService:
    def __init__(
        self,
        interval_seconds: int = 6 * 3600,
        alerts=alert_repository,
        products=product_repository,
        checks=None,
        price_fetcher=None,
    ):
        self.interval = interval_seconds
        self.is_running = False
        self.alerts = alerts
        self.products = products
        self.checks = checks  # PriceCheckRepository; None = không ghi nhật ký
        self.fetch_price = price_fetcher or product_enricher.fetch_current_price
        self._lock = asyncio.Lock()

    async def start(self):
        """Vòng lặp nền: mỗi `interval` giây cập nhật ngưỡng giá theo ngành rồi kiểm tra mọi yêu cầu đang theo dõi."""
        self.is_running = True
        logger.info(f"Khởi động PriceWatcherService (chu kỳ {self.interval}s)")
        while self.is_running:
            await asyncio.sleep(self.interval)
            try:
                await category_floors.refresh()  # ngưỡng giá theo ngành, tính lại khi đã cũ (6 giờ)
                await self.check_alerts()
            except Exception:  # chốt chặn: vòng lặp nền không được dừng vì một lần quét lỗi
                logger.exception("Lỗi khi quét giá")

    def stop(self):
        self.is_running = False

    async def check_alerts(self, alert_ids: Optional[List[str]] = None, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Kiểm tra giá các yêu cầu đang theo dõi (lọc theo alert_ids / user_id); trả về danh sách yêu cầu sau khi cập nhật."""
        async with self._lock:
            watching = [
                a for a in await self.alerts.list(status="watching", user_id=user_id)
                if not alert_ids or a["id"] in alert_ids
            ]
            for alert in watching:
                await self._check_one(alert)
            return await self.alerts.list(user_id=user_id)

    async def _read(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """Đọc giá hiện tại trên sàn của sản phẩm trong yêu cầu; giá không qua guardrails thì price = None."""
        product = {"id": alert["productId"], "name": alert["productName"], "platform": alert["platform"],
                   "externalUrl": alert["productUrl"]}
        fresh = await self.fetch_price(product) or {}
        raw = float(fresh["currentPrice"]) if fresh.get("currentPrice") else None
        current = {**product, "sourceCategoryPath": fresh.get("sourceCategoryPath") or product.get("sourceCategoryPath")}
        await category_resolver.resolve([current])
        verdict = guardrails.check_price(raw, categorize(current))
        return {"price": raw if verdict.ok else None, "raw": raw, "original": fresh.get("originalPrice"),
                "in_stock": fresh.get("inStock"), "verdict": verdict, "readable": bool(fresh)}

    async def _check_one(self, alert: Dict[str, Any]) -> None:
        """Đọc giá -> áp guardrails -> ghi lịch sử giá, cập nhật cảnh báo, ghi nhật ký lần kiểm tra."""
        start = time.perf_counter()
        now = datetime.utcnow()
        reading = await self._read(alert)
        outcome, note, fields = self._evaluate(alert, reading)
        if outcome == "reread":
            outcome, note, fields = await self._confirm_drop(alert, reading, now)
        if outcome in ("accepted", "triggered") and alert["productId"]:
            await self._record_price(alert, reading)
        await self._update_alert(alert, reading, outcome, note, fields, now)
        if self.checks:
            await self.checks.add({
                "alert_id": alert["id"],
                "user_id": alert.get("userId"),
                "product_name": alert["productName"],
                "price": reading["raw"],
                "in_stock": reading["in_stock"],
                "outcome": outcome,
                "note": note,
                "latency_ms": round((time.perf_counter() - start) * 1000.0, 1),
                "checked_at": now,
            })

    async def _confirm_drop(self, alert: Dict[str, Any], reading: Dict[str, Any], now: datetime):
        """D. Sắp báo đạt giá mà giảm mạnh -> đọc lại ngay một lần; hai lần khớp mới chấp nhận, không thì chờ."""
        again = (await self._read(alert))["price"]
        current = reading["price"]
        if guardrails.same_price(again, current):
            return self._accept(alert, reading)
        note = (f"Giá giảm mạnh xuống {_vnd(current)} nhưng lần đọc lại "
                f"{'không đọc được' if again is None else 'cho ' + _vnd(again)}; chưa báo đạt giá.")
        return "pending", note, {"pending_price": current, "pending_at": now}

    async def _record_price(self, alert: Dict[str, Any], reading: Dict[str, Any]) -> None:
        """Ghi mốc lịch sử giá (upsert chỉ thêm mốc khi giá thay đổi)."""
        await self.products.upsert_products([{
            "id": alert["productId"],
            "name": alert["productName"],
            "platform": alert["platform"],
            "platformName": alert["platformName"],
            "currentPrice": reading["price"],
            "originalPrice": reading["original"] or reading["price"],
            "externalUrl": alert["productUrl"],
        }])

    async def _update_alert(self, alert: Dict[str, Any], reading: Dict[str, Any], outcome: str, note: str,
                            fields: Dict[str, Any], now: datetime) -> None:
        update = {"last_checked_at": now, "last_note": note, **fields}
        if reading["readable"]:
            update["in_stock"] = reading["in_stock"]
        if outcome == "triggered":
            update.update(status="triggered", triggered_at=now)
            logger.info(f"[PRICE ALERT] '{alert['productName']}': {note}")
        elif outcome in ("pending", "rejected"):
            logger.warning(f"[Price Guardrail] '{alert['productName']}': {note}")
        await self.alerts.update(alert["id"], **update)

    def _evaluate(self, alert: Dict[str, Any], reading: Dict[str, Any]):
        """Áp guardrails cho một lần đọc -> (outcome, note, fields cần cập nhật). outcome "reread" = cần đọc lại."""
        current = reading["price"]
        if not reading["readable"] or (reading["raw"] is None and reading["in_stock"] is not False):
            return "unreadable", "Không đọc được giá trên trang sản phẩm lần này.", {}

        stock = guardrails.check_stock(reading["in_stock"])
        if not stock.ok:
            price_text = f" (giá niêm yết {_vnd(current)})" if current else ""
            return "out_of_stock", f"{stock.reason.rstrip('.')}{price_text}. Chưa báo đạt giá, sẽ kiểm tra lại.", {}

        if current is None:
            return "rejected", f"Bỏ qua giá đọc được: {reading['verdict'].reason}", {}

        previous = alert["lastPrice"] or alert["initialPrice"]
        confirmed_by_repeat = guardrails.same_price(current, alert.get("pendingPrice"))

        change = guardrails.check_change(current, previous)
        if not change.ok and not confirmed_by_repeat:
            note = f"Giá {_vnd(current)} bất thường ({change.reason}). Chưa ghi nhận, sẽ xác nhận ở lần kiểm tra sau."
            return "pending", note, {"pending_price": current, "pending_at": datetime.utcnow()}

        if current <= alert["targetPrice"] and guardrails.is_big_drop(current, previous) and not confirmed_by_repeat:
            return "reread", "", {}

        outcome, note, fields = self._accept(alert, reading)
        if confirmed_by_repeat and not change.ok and outcome == "accepted":
            note = f"Đã xác nhận giá mới {_vnd(current)} sau 2 lần đọc khớp nhau."
        return outcome, note, fields

    @staticmethod
    def _accept(alert: Dict[str, Any], reading: Dict[str, Any]):
        current = reading["price"]
        fields = {
            "last_price": current,
            "lowest_price": min(current, alert["lowestPrice"] or current),
            "pending_price": None,
            "pending_at": None,
        }
        if current <= alert["targetPrice"]:
            return "triggered", f"Đã đạt giá mong muốn: {_vnd(current)} (mục tiêu {_vnd(alert['targetPrice'])}).", fields
        return "accepted", "", fields


price_watcher_service = PriceWatcherService(checks=price_check_repository)
