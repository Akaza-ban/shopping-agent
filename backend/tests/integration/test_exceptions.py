"""Tầng exception: đổi lỗi thư viện ở ranh giới, chỉ bắt đúng loại lỗi, đổi lỗi nghiệp vụ thành HTTP."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from core.agents.orchestrator import OrchestratorAgent
from core.state import AgentState
from database.errors import raises_database_error
from integrations.llm import ask_llm, parse_llm_json, stream_llm
from integrations.platforms.errors import crawling
from shared.exceptions import (
    AppError,
    CrawlerError,
    DatabaseError,
    DomainError,
    EmailAlreadyRegistered,
    LLMError,
    LLMResponseError,
    NotFoundError,
    PermissionDeniedError,
)
from shared.fallback import fallback
from src.errors import register_error_handlers

logger = logging.getLogger("test_exceptions")


# Cây lỗi
def test_hierarchy():
    assert issubclass(LLMResponseError, LLMError) and issubclass(LLMResponseError, ValueError)
    assert issubclass(EmailAlreadyRegistered, DomainError) and EmailAlreadyRegistered.status_code == 409
    assert all(issubclass(c, AppError) for c in (LLMError, CrawlerError, DatabaseError, NotFoundError))


# LLM
def test_parse_llm_json():
    assert parse_llm_json('```json\n{"intent": "smalltalk"}\n```') == {"intent": "smalltalk"}
    assert parse_llm_json(' {"a": 1} ') == {"a": 1}
    with pytest.raises(LLMResponseError):
        parse_llm_json("không phải json")
    with pytest.raises(LLMResponseError):
        parse_llm_json("[1, 2]")


@pytest.mark.asyncio
async def test_ask_llm_translates_provider_errors():
    model = MagicMock()
    model.ainvoke = AsyncMock(side_effect=TimeoutError("timed out"))
    with pytest.raises(LLMError):
        await ask_llm(model, [])
    with pytest.raises(LLMError):
        await ask_llm(None, [])

    model.ainvoke = AsyncMock(return_value=MagicMock(content="ok"))
    assert await ask_llm(model, []) == "ok"


@pytest.mark.asyncio
async def test_ask_llm_does_not_hide_programming_errors():
    model = MagicMock()
    model.ainvoke = AsyncMock(side_effect=KeyError("bug"))
    with pytest.raises(KeyError):
        await ask_llm(model, [])


@pytest.mark.asyncio
async def test_stream_llm_translates_provider_errors():
    async def broken(messages):
        yield MagicMock(content="xin ")
        raise httpx.ConnectError("mất mạng")

    model = MagicMock()
    model.astream = broken
    tokens = []
    with pytest.raises(LLMError):
        async for token in stream_llm(model, []):
            tokens.append(token)
    assert tokens == ["xin "]


@pytest.mark.asyncio
async def test_orchestrator_falls_back_when_llm_returns_invalid_criteria():
    model = MagicMock()
    model.ainvoke = AsyncMock(
        return_value=MagicMock(content='{"intent": "search_products", "criteria": {"max_price": "abc"}}')
    )
    state = AgentState(session_id="test-exc-route", user_query="tìm laptop dưới 20 triệu")
    with patch("core.agents.orchestrator.get_chat_model", return_value=model):
        result = await OrchestratorAgent().route(state)
    assert result.intent == "search_products"  # phân loại bằng từ khóa
    assert result.criteria is not None and result.criteria.max_price == 20_000_000


# Database
@raises_database_error
class _FakeRepository:
    async def broken(self):
        raise OperationalError("SELECT 1", {}, Exception("database is locked"))

    async def bug(self):
        raise KeyError("bug")

    async def _private(self):
        raise OperationalError("SELECT 1", {}, Exception("locked"))


@pytest.mark.asyncio
async def test_repository_raises_database_error():
    repo = _FakeRepository()
    with pytest.raises(DatabaseError):
        await repo.broken()
    with pytest.raises(KeyError):
        await repo.bug()
    with pytest.raises(OperationalError):  # phương thức nội bộ không bị bọc
        await repo._private()


# Crawler
def test_crawling_translates_known_errors_only():
    with pytest.raises(CrawlerError) as info:
        with crawling("Tiki"):
            raise httpx.ReadTimeout("chậm")
    assert info.value.source == "Tiki" and "[Tiki]" in str(info.value)
    with pytest.raises(ZeroDivisionError):
        with crawling("Tiki"):
            _ = 1 / 0


# fallback()
def test_fallback_swallows_only_listed_errors(caplog):
    with caplog.at_level(logging.WARNING, logger="test_exceptions"):
        with fallback(DatabaseError, "Lỗi đọc cache", logger):
            raise DatabaseError("locked")
    assert "Lỗi đọc cache: locked" in caplog.text
    with pytest.raises(KeyError):
        with fallback(DatabaseError, "Lỗi đọc cache", logger):
            raise KeyError("bug")


# HTTP
def _client() -> TestClient:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/not-found")
    async def not_found():
        raise NotFoundError("Không tìm thấy hội thoại.")

    @app.get("/forbidden")
    async def forbidden():
        raise PermissionDeniedError("Không có quyền.", headers={"X-Reason": "owner"})

    @app.get("/crawler-down")
    async def crawler_down():
        raise CrawlerError("TGDĐ", "502 Bad Gateway")

    @app.get("/db-down")
    async def db_down():
        raise DatabaseError("database is locked")

    return TestClient(app)


def test_domain_errors_become_http_responses():
    client = _client()
    res = client.get("/not-found")
    assert res.status_code == 404 and res.json() == {"detail": "Không tìm thấy hội thoại."}
    res = client.get("/forbidden")
    assert res.status_code == 403 and res.headers["X-Reason"] == "owner"


def test_service_errors_become_503_without_leaking_details():
    client = _client()
    for path in ("/crawler-down", "/db-down"):
        res = client.get(path)
        assert res.status_code == 503
        assert "locked" not in res.text and "Bad Gateway" not in res.text


def test_real_app_auth_error_keeps_bearer_header():
    from src.dependencies.auth import require_user
    from src.main import app

    override = app.dependency_overrides.pop(require_user, None)  # conftest giả lập đã đăng nhập
    try:
        res = TestClient(app).get("/api/auth/me")
    finally:
        if override is not None:
            app.dependency_overrides[require_user] = override
    assert res.status_code == 401
    assert res.headers.get("WWW-Authenticate") == "Bearer"
    assert res.json()["detail"] == "Bạn cần đăng nhập để sử dụng chức năng này."
