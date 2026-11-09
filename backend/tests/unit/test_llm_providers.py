"""Chọn nhà cung cấp LLM: bỏ qua nhà không kết nối được để không phải chờ hết timeout ở mỗi lượt gọi."""

import socket

import pytest

import integrations.llm.client as config


@pytest.fixture(autouse=True)
def fresh_cache(monkeypatch):
    monkeypatch.setattr(config, "_reachability", {})
    monkeypatch.setattr(config.settings, "LLM_PROVIDER", "deepseek")
    monkeypatch.setattr(config.settings, "DEEPSEEK_API_KEY", "khoa-gia-1")
    monkeypatch.setattr(config.settings, "OPENROUTER_API_KEY", "khoa-gia-2")
    monkeypatch.setattr(config.settings, "GROQ_API_KEY", "")


def fake_network(monkeypatch, down, calls=None):
    class Conn:
        def close(self):
            pass

    def connect(address, timeout=None):
        if calls is not None:
            calls.append(address[0])
        if address[0] in down:
            raise OSError("timed out")
        return Conn()

    monkeypatch.setattr(socket, "create_connection", connect)


def bases(model):
    primary = getattr(model, "runnable", model)
    fallbacks = list(getattr(model, "fallbacks", []))
    return [str(m.openai_api_base) for m in [primary, *fallbacks]]


def test_unreachable_provider_is_skipped(monkeypatch):
    fake_network(monkeypatch, {"api.deepseek.com"})
    assert bases(config.get_chat_model()) == ["https://openrouter.ai/api/v1"]


def test_all_reachable_uses_priority_order_with_fallback(monkeypatch):
    fake_network(monkeypatch, set())
    model = config.get_chat_model()
    assert bases(model) == ["https://api.deepseek.com", "https://openrouter.ai/api/v1"]
    # Có dự phòng thì không thử lại nhà cung cấp đang lỗi
    assert model.runnable.max_retries == 0


def test_everything_unreachable_still_returns_a_model(monkeypatch):
    fake_network(monkeypatch, {"api.deepseek.com", "openrouter.ai"})
    assert config.get_chat_model() is not None


def test_reachability_is_cached(monkeypatch):
    calls = []
    fake_network(monkeypatch, {"api.deepseek.com"}, calls)
    config.get_chat_model()
    config.get_chat_model()
    assert calls.count("api.deepseek.com") == 1


def test_recovers_after_cache_expires(monkeypatch):
    fake_network(monkeypatch, {"api.deepseek.com"})
    assert config.is_reachable("https://api.deepseek.com") is False
    fake_network(monkeypatch, set())
    config._reachability["api.deepseek.com"] = (0.0, False)  # hết hạn ghi nhớ
    assert config.is_reachable("https://api.deepseek.com") is True
