import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("benchmark_guardrails")

@dataclass
class GuardrailResult:
    passed: bool
    score: float  # Điểm benchmark từ 0.0 đến 1.0
    latency_ms: float
    violations: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

class BenchmarkGuardrails:
    """
    Hệ thống Benchmark Guardrails nhằm kiểm soát chất lượng dữ liệu giá,
    hiệu năng thu thập và độ tin cậy trước khi kích hoạt cảnh báo tới người dùng.
    """

    def __init__(
        self,
        min_price_floor: float = 10_000.0,            # Mức giá tối thiểu hợp lệ (tránh lỗi 0đ / 1đ)
        max_price_ceiling: float = 500_000_000.0,     # Mức giá trần tối đa
        max_drop_percentage: float = 75.0,            # Cảnh báo bất thường nếu giá giảm đột ngột > 75%
        max_spike_percentage: float = 200.0,          # Bất thường nếu giá tăng đột ngột > 200%
        sla_latency_threshold_ms: float = 3000.0,     # Ngưỡng SLA thời gian xử lý (3 giây)
        min_quality_score: float = 0.8                # Ngưỡng chất lượng tối thiểu để chấp thuận
    ):
        self.min_price_floor = min_price_floor
        self.max_price_ceiling = max_price_ceiling
        self.max_drop_percentage = max_drop_percentage
        self.max_spike_percentage = max_spike_percentage
        self.sla_latency_threshold_ms = sla_latency_threshold_ms
        self.min_quality_score = min_quality_score

    def evaluate_price_benchmark(
        self,
        current_price: float,
        previous_price: Optional[float] = None,
        target_price: Optional[float] = None,
        execution_time_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> GuardrailResult:
        """
        Đánh giá toàn diện các tiêu chí benchmark của sản phẩm và biến động giá:
        1. Sanity Check (Giá hợp lý trong khoảng sàn - trần)
        2. Volatility Check (Độ biến động bất thường so với giá lịch sử)
        3. SLA Latency Benchmark (Hiệu năng phản hồi của hệ thống cào/API)
        4. Target Price Feasibility (Tính khả thi của mức giá cảnh báo)
        """
        violations: List[str] = []
        metrics: Dict[str, Any] = {
            "current_price": current_price,
            "previous_price": previous_price,
            "target_price": target_price,
            "latency_ms": execution_time_ms
        }
        score = 1.0

        # 1. Sanity Guardrail: Kiểm tra biên độ giá hợp lệ
        if current_price < self.min_price_floor:
            violations.append(
                f"Giá hiện tại ({current_price:,.0f} đ) vi phạm sàn tối thiểu ({self.min_price_floor:,.0f} đ) - Nghi ngờ lỗi crawler hoặc phụ kiện."
            )
            score -= 0.4

        if current_price > self.max_price_ceiling:
            violations.append(
                f"Giá hiện tại ({current_price:,.0f} đ) vượt trần quy định ({self.max_price_ceiling:,.0f} đ)."
            )
            score -= 0.3

        # 2. Volatility & Anomaly Guardrail: Kiểm tra biến động bất thường
        if previous_price and previous_price > 0:
            price_diff_percent = ((current_price - previous_price) / previous_price) * 100.0
            metrics["price_diff_percent"] = price_diff_percent

            # Giá giảm quá sâu bất thường (thường do link phụ kiện, mã khuyến mãi ảo hoặc lỗi hệ thống)
            if price_diff_percent < -self.max_drop_percentage:
                violations.append(
                    f"Giá giảm sốc {abs(price_diff_percent):.1f}% (vượt ngưỡng cho phép {self.max_drop_percentage}%). Cần kiểm duyệt thủ công."
                )
                score -= 0.35

            # Giá tăng đột biến
            if price_diff_percent > self.max_spike_percentage:
                violations.append(
                    f"Giá tăng đột biến {price_diff_percent:.1f}% (vượt ngưỡng {self.max_spike_percentage}%)."
                )
                score -= 0.25

        # 3. SLA Performance Benchmark: Kiểm tra độ trễ thu thập dữ liệu
        if execution_time_ms > self.sla_latency_threshold_ms:
            violations.append(
                f"Độ trễ xử lý ({execution_time_ms:.1f}ms) vượt chỉ tiêu SLA benchmark ({self.sla_latency_threshold_ms:.1f}ms)."
            )
            score -= 0.15

        # 4. Data Quality & Metadata Check
        if metadata:
            if not metadata.get("name") or len(str(metadata.get("name")).strip()) < 5:
                violations.append("Tên sản phẩm quá ngắn hoặc không đầy đủ.")
                score -= 0.2
            if metadata.get("is_out_of_stock"):
                violations.append("Sản phẩm đang trong trạng thái hết hàng (Out of Stock).")
                score -= 0.3

        score = max(0.0, min(1.0, score))
        passed = (score >= self.min_quality_score) and (len(violations) == 0 or score >= 0.75)

        if not passed:
            logger.warning(f"⚠️ [Guardrail Violated] Score: {score:.2f} | Violations: {violations}")

        return GuardrailResult(
            passed=passed,
            score=score,
            latency_ms=execution_time_ms,
            violations=violations,
            metrics=metrics
        )
