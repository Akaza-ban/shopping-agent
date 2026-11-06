"""
Cấu hình chung cho pytest: các test API cũ (viết trước khi có đăng nhập) chạy như một quản trị viên đã đăng nhập.
tests/test_auth.py kiểm thử xác thực thật nên không áp dụng.
"""
import gc
from types import SimpleNamespace

import pytest

TEST_USER = SimpleNamespace(id="user-test", email="tester@shop.vn", display_name="Tester", role="admin")


@pytest.fixture(autouse=True)
def _release_llm_clients():
    # Mỗi test async có event loop riêng. Client của SDK OpenAI bị thu hồi trong loop của test sau sẽ đóng kết nối
    # thuộc loop đã đóng ("Event loop is closed"); thu hồi ngay sau mỗi test, lúc chưa có loop nào chạy.
    yield
    gc.collect()


@pytest.fixture(autouse=True)
def _logged_in_user(request):
    if request.module.__name__.endswith("test_auth"):
        yield
        return
    from src.main import app
    from src.auth import require_user, require_admin

    app.dependency_overrides[require_user] = lambda: TEST_USER
    app.dependency_overrides[require_admin] = lambda: TEST_USER
    yield
    app.dependency_overrides.pop(require_user, None)
    app.dependency_overrides.pop(require_admin, None)


# Kết quả quy đổi "đã học" cho các danh mục xuất hiện trong dữ liệu mẫu của test (đóng vai bảng category_mappings)
TEST_CATEGORY_MAPPINGS = {
    "tiki:1/2/1846/8095": ("laptops", False),
    "tiki:1/2/6000/27608": ("other", True),
    "tiki:1/2/1815/8215": ("audio", False),
    "tiki:1815/8215": ("audio", False),
    "tiki:1/2/1951": ("home_appliances", False),
    "tgdd:laptop": ("laptops", False),
    "tgdd:dtdd": ("phones", False),
    "tgdd:op-lung-iphone": ("other", True),
    "dmx:may-giat": ("home_appliances", False),
    "fpt-shop:/may-tinh-xach-tay": ("laptops", False),
    # Đường dẫn 3 cấp Ngành/Loại/Nhóm của FPT Shop (test gọi trang thật)
    "fpt-shop:Điện thoại/iPhone (IOS)": ("phones", False),
    "fpt-shop:Điện thoại/iPhone (IOS)/iPhone 16 Series": ("phones", False),
    "fpt-shop:Phụ kiện/MDMH": ("other", True),
}


@pytest.fixture(autouse=True)
def _offline_category_resolver(monkeypatch):
    """Quy đổi danh mục không gọi LLM / CSDL thật trong test; test cần thì tự nạp bằng category_resolver.remember()."""
    from services.catalog.category_resolver import category_resolver

    class _MemoryRepo:
        async def all(self):
            return []

        async def save(self, rows):
            pass

    async def _no_llm(items):
        return None

    saved = dict(category_resolver._cache)
    category_resolver._cache.clear()
    category_resolver.remember(TEST_CATEGORY_MAPPINGS)
    monkeypatch.setattr(category_resolver, "_repository", _MemoryRepo())
    monkeypatch.setattr(category_resolver, "_loaded", True)
    monkeypatch.setattr(category_resolver, "_classify", _no_llm)

    async def _unknown_same_kind(products):
        return None

    monkeypatch.setattr(category_resolver, "same_kind", _unknown_same_kind)
    yield category_resolver
    category_resolver._cache.clear()
    category_resolver._cache.update(saved)


@pytest.fixture(autouse=True)
def _fixed_category_floors():
    """Ngưỡng giá theo ngành thường tính từ kho thật; test dùng giá trị cố định để không phụ thuộc dữ liệu."""
    from services.pricing.category_floors import category_floors
    saved = dict(category_floors._floors)
    category_floors.set({"laptops": 2_000_000.0, "phones": 500_000.0})
    yield category_floors
    category_floors.set(saved)
