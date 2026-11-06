import asyncio
import time
import logging
from typing import List, Dict, Any, Optional
from .guardrails import BenchmarkGuardrails, GuardrailResult

logger = logging.getLogger("price_watcher")

class PriceWatcherService:
    """Service chạy nền (background worker) theo dõi biến động giá định kỳ với Benchmark Guardrails."""

    def __init__(
        self,
        interval_seconds: int = 3600,
        guardrails: Optional[BenchmarkGuardrails] = None
    ):
        self.interval = interval_seconds
        self.is_running = False
        # Khởi tạo Benchmark Guardrails để giám sát chất lượng và tính hợp lệ của giá
        self.guardrails = guardrails or BenchmarkGuardrails(
            min_price_floor=10_000.0,
            max_drop_percentage=75.0,
            sla_latency_threshold_ms=2500.0,
            min_quality_score=0.8
        )
        # Lưu nhật ký audit của các lần kiểm tra benchmark
        self.audit_log: List[Dict[str, Any]] = []

    async def start(self):
        self.is_running = True
        logger.info(f"🚀 Khởi động PriceWatcherService kèm Benchmark Guardrails (Chu kỳ: {self.interval}s)")
        while self.is_running:
            try:
                # Quét giá các sản phẩm đang được theo dõi
                await self._check_price_drops()
            except Exception as e:
                logger.error(f"❌ Lỗi khi quét giá: {e}")
            await asyncio.sleep(self.interval)

    async def _check_price_drops(self):
        """
        Quét danh sách các sản phẩm đang được kích hoạt Price Alert,
        áp dụng Benchmark Guardrails trước khi phát sinh thông báo tới người dùng.
        """
        # Lấy danh sách alert thực tế do người dùng tạo
        from src.routes.alerts import _ALERTS_DB
        active_alerts = [alert.model_dump() for alert in _ALERTS_DB]
        if not active_alerts:
            return

        for item in active_alerts:
            start_time = time.perf_counter()

            # Giả lập thời gian crawler thực thi để đo benchmark SLA
            await asyncio.sleep(0.05)
            execution_time_ms = (time.perf_counter() - start_time) * 1000.0

            # 🛡️ ÁP DỤNG BENCHMARK GUARDRAILS
            evaluation: GuardrailResult = self.guardrails.evaluate_price_benchmark(
                current_price=item["current_price"],
                previous_price=item["previous_price"],
                target_price=item["target_price"],
                execution_time_ms=execution_time_ms,
                metadata={"name": item["product_name"]}
            )

            # Lưu vào nhật ký Audit
            audit_entry = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "product": item["product_name"],
                "guardrail_passed": evaluation.passed,
                "benchmark_score": round(evaluation.score, 3),
                "latency_ms": round(evaluation.latency_ms, 2),
                "violations": evaluation.violations
            }
            self.audit_log.append(audit_entry)

            # Chỉ kích hoạt thông báo khi VƯỢT QUA BENCHMARK GUARDRAILS
            if evaluation.passed:
                if item["current_price"] <= item["target_price"]:
                    logger.info(
                        f"🎯 [PRICE ALERT SUCCESS] Sản phẩm '{item['product_name']}' đạt mức giá mục tiêu: "
                        f"{item['current_price']:,.0f} đ (Target: {item['target_price']:,.0f} đ). "
                        f"Điểm Benchmark: {evaluation.score:.2f}"
                    )
                    await self._notify_user(item, evaluation)
            else:
                logger.warning(
                    f"⛔ [GUARDRAIL REJECTED] Bỏ qua cảnh báo cho '{item['product_name']}' do vi phạm Benchmark: "
                    f"{evaluation.violations}"
                )

    async def _notify_user(self, alert_item: Dict[str, Any], evaluation: GuardrailResult):
        """Hàm gửi thông báo (Email / Webhook / In-App Notification)."""
        logger.info(f"📧 Đã gửi thông báo giảm giá tới email: {alert_item['user_email']}")

    def get_audit_metrics(self) -> List[Dict[str, Any]]:
        """Lấy danh sách các bản ghi benchmark metrics gần nhất."""
        return self.audit_log[-50:]

    def stop(self):
        self.is_running = False

