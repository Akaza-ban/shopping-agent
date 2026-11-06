import pytest
from services.guardrails import BenchmarkGuardrails

def test_guardrail_valid_price_drop():
    guardrails = BenchmarkGuardrails(
        min_price_floor=10_000.0,
        max_drop_percentage=75.0,
        sla_latency_threshold_ms=2500.0
    )
    
    # Giá giảm hợp lý: 30 triệu -> 25 triệu (~ 16.7%)
    result = guardrails.evaluate_price_benchmark(
        current_price=25_000_000.0,
        previous_price=30_000_000.0,
        target_price=26_000_000.0,
        execution_time_ms=120.0,
        metadata={"name": "Laptop Gaming ASUS"}
    )
    
    assert result.passed is True
    assert result.score >= 0.8
    assert len(result.violations) == 0

def test_guardrail_anomalous_price_drop():
    guardrails = BenchmarkGuardrails(
        max_drop_percentage=75.0
    )
    
    # Giá giảm bất thường 95% (nghi ngờ lỗi hệ thống hoặc phụ kiện)
    result = guardrails.evaluate_price_benchmark(
        current_price=1_000_000.0,
        previous_price=20_000_000.0,
        target_price=15_000_000.0,
        execution_time_ms=150.0,
        metadata={"name": "Laptop Dell XPS"}
    )
    
    assert result.passed is False
    assert any("Giá giảm sốc" in v for v in result.violations)

def test_guardrail_latency_sla_breach():
    guardrails = BenchmarkGuardrails(
        sla_latency_threshold_ms=1000.0
    )
    
    # Thời gian xử lý 3500ms vượt quá SLA benchmark 1000ms
    result = guardrails.evaluate_price_benchmark(
        current_price=15_000_000.0,
        previous_price=16_000_000.0,
        execution_time_ms=3500.0
    )
    
    assert any("vượt chỉ tiêu SLA benchmark" in v for v in result.violations)
