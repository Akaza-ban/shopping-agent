"""
Kiểm thử đăng ký / đăng nhập và phân quyền (chạy offline với SQLite tạm, không đụng shopai.db):
- Đăng ký, đăng nhập, /me, đăng xuất thu hồi token, đổi mật khẩu.
- Kiểm tra dữ liệu: email trùng, mật khẩu yếu, sai mật khẩu, khóa tạm sau nhiều lần sai.
- API riêng tư yêu cầu token; hội thoại và theo dõi giá tách biệt giữa các người dùng; quyền quản trị.
- Đồng bộ dữ liệu cá nhân theo tài khoản.
"""
import asyncio
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from database.repositories import (
    user_repository, alert_repository, chat_repository, product_repository, price_check_repository, feedback_repository,
)
from services.auth.service import login_throttle, validate_password, hash_password, verify_password
from shared.config import settings

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'auth.db'}")

    async def setup():
        async with engine.begin() as conn:
            from database import models  # noqa: F401
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(setup())
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    for repo in (user_repository, alert_repository, chat_repository, product_repository, price_check_repository,
                 feedback_repository):
        monkeypatch.setattr(repo, "session_factory", factory)
    monkeypatch.setattr(settings, "ADMIN_EMAILS", "admin@shop.vn")
    login_throttle._failures.clear()

    from src.main import app
    yield TestClient(app)  # không dùng "with" -> không chạy lifespan (làm ấm kho, theo dõi giá)
    login_throttle._failures.clear()


def register(client, email="an@shop.vn", password="matkhau123", name="Nguyễn An"):
    return client.post("/api/auth/register", json={"email": email, "password": password, "display_name": name})


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------- dịch vụ
def test_password_rules_and_hashing():
    assert validate_password("abc12") and validate_password("chiluchu") and validate_password("12345678")
    assert validate_password("matkhau123") == []
    h = hash_password("matkhau123")
    assert h != "matkhau123" and verify_password("matkhau123", h) and not verify_password("sai", h)


# ---------------------------------------------------------------- đăng ký / đăng nhập
def test_register_login_me_logout(client):
    res = register(client, email="  An@Shop.VN ")
    assert res.status_code == 201
    body = res.json()
    assert body["user"]["email"] == "an@shop.vn" and body["user"]["role"] == "user"
    assert "password" not in str(body["user"]).lower()

    login = client.post("/api/auth/login", json={"email": "an@shop.vn", "password": "matkhau123"})
    assert login.status_code == 200
    token = login.json()["token"]
    assert client.get("/api/auth/me", headers=auth(token)).json()["displayName"] == "Nguyễn An"

    assert client.post("/api/auth/logout", headers=auth(token)).status_code == 200
    assert client.get("/api/auth/me", headers=auth(token)).status_code == 401  # token đã bị thu hồi


def test_register_validation_and_duplicate(client):
    assert register(client, email="khong-phai-email").status_code == 422
    assert register(client, password="ngan1").status_code == 422
    assert register(client, name="A").status_code == 422
    assert register(client).status_code == 201
    dup = register(client, email="AN@shop.vn")
    assert dup.status_code == 409 and "đã được đăng ký" in dup.json()["detail"]


def test_wrong_password_same_message_and_lockout(client):
    register(client)
    wrong = client.post("/api/auth/login", json={"email": "an@shop.vn", "password": "saimatkhau1"})
    unknown = client.post("/api/auth/login", json={"email": "khongco@shop.vn", "password": "saimatkhau1"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"]
    for _ in range(4):
        client.post("/api/auth/login", json={"email": "an@shop.vn", "password": "saimatkhau1"})
    locked = client.post("/api/auth/login", json={"email": "an@shop.vn", "password": "matkhau123"})
    assert locked.status_code == 429


def test_change_password_revokes_other_sessions(client):
    t1 = register(client).json()["token"]
    t2 = client.post("/api/auth/login", json={"email": "an@shop.vn", "password": "matkhau123"}).json()["token"]
    bad = client.post("/api/auth/change-password", headers=auth(t1), json={"current_password": "x", "new_password": "moi12345a"})
    assert bad.status_code == 400
    ok = client.post("/api/auth/change-password", headers=auth(t1), json={"current_password": "matkhau123", "new_password": "moi12345a"})
    assert ok.status_code == 200
    assert client.get("/api/auth/me", headers=auth(t1)).status_code == 200  # phiên hiện tại giữ nguyên
    assert client.get("/api/auth/me", headers=auth(t2)).status_code == 401  # thiết bị khác bị đăng xuất
    assert client.post("/api/auth/login", json={"email": "an@shop.vn", "password": "moi12345a"}).status_code == 200


# ---------------------------------------------------------------- phân quyền
def test_private_apis_require_login(client):
    for method, path in [("get", "/api/alerts"), ("post", "/api/chat/compare"), ("get", "/api/chat/history/x"),
                         ("get", "/api/products/search?q=laptop"), ("get", "/api/crawler/status")]:
        assert getattr(client, method)(path).status_code == 401, path


def test_admin_only_crawler_trigger(client):
    user = register(client).json()["token"]
    admin = register(client, email="admin@shop.vn", name="Quản trị").json()
    assert admin["user"]["role"] == "admin"
    assert client.post("/api/crawler/trigger", headers=auth(user), json={"background": True}).status_code == 403
    assert client.get("/api/alerts/metrics", headers=auth(user)).status_code == 403
    assert client.get("/api/alerts/metrics", headers=auth(admin["token"])).status_code == 200


def test_conversations_are_private(client):
    a = register(client).json()["token"]
    b = register(client, email="binh@shop.vn", name="Trần Bình").json()["token"]
    user_a = client.get("/api/auth/me", headers=auth(a)).json()["id"]
    assert asyncio.run(chat_repository.claim_session("chat-cua-a", user_a, "laptop"))
    assert client.get("/api/chat/history/chat-cua-a", headers=auth(a)).status_code == 200
    assert client.get("/api/chat/history/chat-cua-a", headers=auth(b)).status_code == 403
    assert client.delete("/api/chat/history/chat-cua-a", headers=auth(b)).status_code == 403


def test_price_alerts_are_private(client, monkeypatch):
    from jobs.price_watcher import price_watcher_service

    async def live_price(product):  # giá gốc do server đọc từ sàn, không lấy giá client gửi
        return {"currentPrice": 21_000_000, "originalPrice": 22_000_000}

    monkeypatch.setattr(price_watcher_service, "fetch_price", live_price)
    a = register(client).json()["token"]
    b = register(client, email="binh@shop.vn", name="Trần Bình").json()["token"]
    product = {"id": "tgdd-test-1", "name": "Laptop thử nghiệm", "platform": "tgdd", "platformName": "TGDĐ",
               "currentPrice": 20_000_000, "externalUrl": "https://example.com/p"}
    created = client.post("/api/alerts", headers=auth(a), json={"product": product, "target_price": 18_000_000})
    assert created.status_code == 200 and created.json()["userEmail"] == "an@shop.vn"
    assert created.json()["initialPrice"] == 21_000_000
    too_high = client.post("/api/alerts", headers=auth(a), json={"product": product, "target_price": 21_500_000})
    assert too_high.status_code == 400 and "21.000.000" in too_high.json()["detail"]
    alert_id = created.json()["id"]
    assert len(client.get("/api/alerts", headers=auth(a)).json()) == 1
    assert client.get("/api/alerts", headers=auth(b)).json() == []
    assert client.get(f"/api/alerts/{alert_id}/checks", headers=auth(a)).json() == []
    assert client.get(f"/api/alerts/{alert_id}/checks", headers=auth(b)).status_code == 404
    assert client.delete(f"/api/alerts/{alert_id}", headers=auth(b)).status_code == 404
    assert client.delete(f"/api/alerts/{alert_id}", headers=auth(a)).status_code == 200


# ---------------------------------------------------------------- dữ liệu cá nhân
def test_user_data_sync(client):
    a = register(client).json()["token"]
    b = register(client, email="binh@shop.vn", name="Trần Bình").json()["token"]
    saved = [{"product": {"id": "p1", "name": "Máy giặt"}, "savedAt": "29/10"}]
    assert client.put("/api/auth/me/data/saved-products", headers=auth(a), json={"value": saved}).status_code == 200
    assert client.get("/api/auth/me/data/saved-products", headers=auth(a)).json()["value"] == saved
    assert client.get("/api/auth/me/data/saved-products", headers=auth(b)).json()["value"] is None
    assert client.get("/api/auth/me/data/khong-ton-tai", headers=auth(a)).status_code == 404
    # Cài đặt người dùng (giao diện, ngôn ngữ) lưu theo tài khoản
    prefs = {"themeMode": "auto", "darkFrom": "19:00", "darkTo": "06:30", "language": "en"}
    assert client.put("/api/auth/me/data/preferences", headers=auth(a), json={"value": prefs}).status_code == 200
    assert client.get("/api/auth/me/data/preferences", headers=auth(a)).json()["value"] == prefs
    assert client.get("/api/auth/me/data/preferences", headers=auth(b)).json()["value"] is None


# ---------------------------------------------------------------- góp ý / yêu cầu hỗ trợ
def test_feedback_reaches_admin(client):
    user = register(client).json()["token"]
    admin = register(client, email="admin@shop.vn", name="Quản trị").json()["token"]

    sent = client.post("/api/feedback", headers=auth(user), json={
        "kind": "support", "topic": "Sai giá / sai thông tin", "content": "  Giá máy giặt Aqua bị sai  ", "contact": "0901234567"})
    assert sent.status_code == 201
    item = sent.json()
    assert item["status"] == "new" and item["content"] == "Giá máy giặt Aqua bị sai"
    assert item["userEmail"] == "an@shop.vn" and item["userName"] == "Nguyễn An"
    client.post("/api/feedback", headers=auth(user), json={"kind": "feedback", "topic": "Giao diện", "content": "Thêm chế độ tối"})

    # Người dùng thường không xem / sửa được hộp thư của admin, chỉ xem yêu cầu của mình
    assert client.get("/api/feedback", headers=auth(user)).status_code == 403
    assert client.patch(f"/api/feedback/{item['id']}", headers=auth(user), json={"status": "resolved"}).status_code == 403
    assert len(client.get("/api/feedback/mine", headers=auth(user)).json()) == 2
    assert client.get("/api/feedback/mine", headers=auth(admin)).json() == []

    inbox = client.get("/api/feedback", headers=auth(admin)).json()
    assert inbox["counts"] == {"new": 2, "in_progress": 0, "resolved": 0}
    assert [i["kind"] for i in inbox["items"]] == ["feedback", "support"]  # mới nhất trước
    assert len(client.get("/api/feedback?kind=support", headers=auth(admin)).json()["items"]) == 1

    done = client.patch(f"/api/feedback/{item['id']}", headers=auth(admin),
                        json={"status": "resolved", "admin_note": "Đã báo đội dữ liệu"}).json()
    assert done["status"] == "resolved" and done["adminNote"] == "Đã báo đội dữ liệu"
    assert client.get("/api/feedback", headers=auth(admin)).json()["counts"] == {"new": 1, "in_progress": 0, "resolved": 1}
    assert client.patch("/api/feedback/fb-khong-co", headers=auth(admin), json={"status": "resolved"}).status_code == 404


def test_feedback_validation_and_rate_limit(client, monkeypatch):
    user = register(client).json()["token"]
    assert client.post("/api/feedback", json={"kind": "feedback", "content": "x"}).status_code == 401
    for bad in [{"kind": "feedback", "content": "   "}, {"kind": "khac", "content": "x"},
                {"kind": "feedback", "content": "x" * 4001}]:
        assert client.post("/api/feedback", headers=auth(user), json=bad).status_code == 422, bad
    admin = register(client, email="admin@shop.vn", name="Quản trị").json()["token"]
    assert client.patch("/api/feedback/x", headers=auth(admin), json={"status": "xong"}).status_code == 422

    import application.feedback as feedback_app
    monkeypatch.setattr(feedback_app, "MAX_PER_HOUR", 2)
    codes = [client.post("/api/feedback", headers=auth(user), json={"kind": "feedback", "content": f"góp ý {i}"}).status_code
             for i in range(3)]
    assert codes == [201, 201, 429]



# ---------------------------------------------------------------- quên mật khẩu
@pytest.fixture()
def outbox(monkeypatch):
    """Email đặt lại mật khẩu gửi đi (không gửi thật): [(người nhận, link)]."""
    sent = []

    async def fake_send(to, name, link, ttl_minutes):
        sent.append((to, link))
        return True

    import application.auth as auth_app
    monkeypatch.setattr(auth_app, "send_password_reset", fake_send)
    return sent


def _token_from(link):
    from urllib.parse import parse_qs, urlparse
    return parse_qs(urlparse(link).query)["reset_token"][0]


def test_forgot_password_full_flow(client, outbox):
    old = register(client).json()["token"]
    other_device = client.post("/api/auth/login", json={"email": "an@shop.vn", "password": "matkhau123"}).json()["token"]

    r = client.post("/api/auth/forgot-password", json={"email": "  AN@shop.vn "})
    assert r.status_code == 200 and r.json()["ok"]
    assert len(outbox) == 1 and outbox[0][0] == "an@shop.vn"
    assert outbox[0][1].startswith(settings.FRONTEND_URL.rstrip("/") + "/?reset_token=")
    token = _token_from(outbox[0][1])
    assert client.get("/api/auth/reset-password/check", params={"token": token}).json() == {"valid": True, "email": "an@shop.vn"}

    # Mật khẩu mới yếu -> từ chối, link vẫn còn dùng được
    assert client.post("/api/auth/reset-password", json={"token": token, "new_password": "ngan"}).status_code == 422
    assert client.post("/api/auth/reset-password", json={"token": token, "new_password": "matkhaumoi9"}).status_code == 200

    # Mọi phiên cũ bị đăng xuất; mật khẩu cũ hết tác dụng, mật khẩu mới đăng nhập được
    assert client.get("/api/auth/me", headers=auth(old)).status_code == 401
    assert client.get("/api/auth/me", headers=auth(other_device)).status_code == 401
    assert client.post("/api/auth/login", json={"email": "an@shop.vn", "password": "matkhau123"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "an@shop.vn", "password": "matkhaumoi9"}).status_code == 200

    # Link chỉ dùng được một lần
    assert client.post("/api/auth/reset-password", json={"token": token, "new_password": "matkhaukhac7"}).status_code == 400
    assert client.get("/api/auth/reset-password/check", params={"token": token}).json()["valid"] is False


def test_forgot_password_does_not_reveal_accounts(client, outbox):
    register(client)
    known = client.post("/api/auth/forgot-password", json={"email": "an@shop.vn"})
    unknown = client.post("/api/auth/forgot-password", json={"email": "chua-dang-ky@shop.vn"})
    assert known.status_code == unknown.status_code == 200 and known.json() == unknown.json()
    assert [to for to, _ in outbox] == ["an@shop.vn"]
    assert client.post("/api/auth/forgot-password", json={"email": "khong-phai-email"}).status_code == 422


def test_reset_link_rules(client, outbox, monkeypatch):
    register(client)
    client.post("/api/auth/forgot-password", json={"email": "an@shop.vn"})
    first = _token_from(outbox[-1][1])
    client.post("/api/auth/forgot-password", json={"email": "an@shop.vn"})
    second = _token_from(outbox[-1][1])
    # Link mới thay link cũ
    assert client.get("/api/auth/reset-password/check", params={"token": first}).json()["valid"] is False
    assert client.get("/api/auth/reset-password/check", params={"token": second}).json()["valid"] is True
    assert client.post("/api/auth/reset-password", json={"token": "bịa-ra", "new_password": "matkhaumoi9"}).status_code == 400

    # Giới hạn 3 link / giờ: lần thứ 4 vẫn trả lời như bình thường nhưng không gửi email
    client.post("/api/auth/forgot-password", json={"email": "an@shop.vn"})
    client.post("/api/auth/forgot-password", json={"email": "an@shop.vn"})
    assert len(outbox) == 3

    # Link hết hạn
    from datetime import datetime, timedelta
    import database.repositories.user_repo as user_repo_module

    class Later(datetime):
        @classmethod
        def utcnow(cls):
            return datetime.utcnow() + timedelta(minutes=settings.PASSWORD_RESET_TTL_MINUTES + 1)

    monkeypatch.setattr(user_repo_module, "datetime", Later)
    latest = _token_from(outbox[-1][1])
    assert client.post("/api/auth/reset-password", json={"token": latest, "new_password": "matkhaumoi9"}).status_code == 400


def test_dev_mailer_logs_link_without_smtp(monkeypatch, caplog):
    import integrations.mail as mailer
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    with caplog.at_level("WARNING", logger="mailer"):
        assert asyncio.run(mailer.send_password_reset("an@shop.vn", "An", "http://x/?reset_token=abc", 30)) is True
    assert "reset_token=abc" in caplog.text
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    caplog.clear()
    assert asyncio.run(mailer.send_password_reset("an@shop.vn", "An", "http://x/?reset_token=abc", 30)) is False
    assert "reset_token=abc" not in caplog.text  # môi trường thật không ghi link ra log
