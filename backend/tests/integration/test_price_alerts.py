"""
Kiểm thử theo dõi giá (chạy offline): DB SQLite tạm, giá hiện tại do hàm giả cung cấp.
- Đọc giá TGDĐ/ĐMX từ JSON-LD.
- Đạt giá mong muốn -> "triggered" + ghi mốc lịch sử giá; chưa đạt -> vẫn "watching".
- Giá bất thường (giảm > 75%) bị guardrail chặn, không báo nhầm; lần đọc sau khớp thì xác nhận là giá mới.
- Giảm mạnh (> 30%) tới mức mong muốn -> đọc lại ngay, khớp mới báo đạt giá.
- Sàn báo hết hàng -> không báo đạt giá. Mỗi lần kiểm tra ghi vào bảng price_checks.
- init_db bổ sung cột mới vào bảng price_alerts cũ.
"""

import asyncio
import sys

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base, _add_missing_columns
from database.repositories.alert_repo import AlertRepository, PriceCheckRepository
from database.repositories.product_repo import ProductRepository
from integrations.platforms.common import parse_availability as parse_mwg_availability
from integrations.platforms.common import parse_offer_price as parse_mwg_price
from jobs.price_watcher import PriceWatcherService

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


def test_parse_mwg_price_from_json_ld():
    html = """<html><head><script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "Product", "name": "Laptop X",
     "offers": {"@type": "Offer", "price": "22990000", "priceCurrency": "VND"}}
    </script></head><body>27.990.000₫</body></html>"""
    assert parse_mwg_price(html) == 22_990_000
    assert parse_mwg_price("<html></html>") is None


def test_parse_mwg_availability():
    ld = '<script type="application/ld+json">{"offers": {"price": "100000", "availability": "%s"}}</script>'
    assert parse_mwg_availability(ld % "https://schema.org/InStock") is True
    assert parse_mwg_availability(ld % "https://schema.org/OutOfStock") is False
    assert parse_mwg_availability(ld % "http://schema.org/Discontinued") is False
    assert parse_mwg_availability("<div>Sản phẩm ngừng kinh doanh</div>".replace("ngừng", "Ngừng")) is False
    assert parse_mwg_availability("<html></html>") is None


async def _setup(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'alerts.db'}")
    async with engine.begin() as conn:
        from database import models  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, AlertRepository(factory), ProductRepository(factory)


async def _new_alert(alerts, products, pid, price, target):
    await products.upsert_products(
        [
            {
                "id": pid,
                "name": f"Laptop thử nghiệm {pid}",
                "platform": "tgdd",
                "platformName": "TGDĐ",
                "currentPrice": price,
                "externalUrl": f"https://www.thegioididong.com/laptop/{pid}",
            }
        ]
    )
    return await alerts.create(
        {
            "id": f"alert-{pid}",
            "product_id": pid,
            "product_name": f"Laptop thử nghiệm {pid}",
            "product_url": f"https://www.thegioididong.com/laptop/{pid}",
            "platform": "tgdd",
            "platform_name": "TGDĐ",
            "target_price": target,
            "initial_price": price,
            "last_price": price,
            "lowest_price": price,
            "status": "watching",
        }
    )


def test_watcher_triggers_and_records_history(tmp_path):
    async def scenario():
        engine, alerts, products = await _setup(tmp_path)
        await _new_alert(alerts, products, "hit", 25_000_000, 23_000_000)
        await _new_alert(alerts, products, "miss", 25_000_000, 20_000_000)
        await _new_alert(alerts, products, "crash", 25_000_000, 20_000_000)

        fresh = {"hit": 22_500_000, "miss": 24_000_000, "crash": 2_000_000}

        async def fake_price(product):
            return {"currentPrice": fresh[product["id"]], "originalPrice": 25_000_000}

        watcher = PriceWatcherService(alerts=alerts, products=products, price_fetcher=fake_price)
        result = {a["productId"]: a for a in await watcher.check_alerts()}
        history = await products.get_price_history("hit")
        await engine.dispose()
        return result, history

    result, history = asyncio.run(scenario())
    assert result["hit"]["status"] == "triggered" and result["hit"]["lastPrice"] == 22_500_000
    assert "Đã đạt giá mong muốn" in result["hit"]["lastNote"]
    assert result["miss"]["status"] == "watching" and result["miss"]["lowestPrice"] == 24_000_000
    # Giảm 92% -> guardrail chặn, giữ giá cũ
    assert result["crash"]["status"] == "watching" and result["crash"]["lastPrice"] == 25_000_000
    assert "bất thường" in result["crash"]["lastNote"]
    assert [h["price"] for h in history] == [25_000_000, 22_500_000]


def test_watcher_handles_unreadable_price(tmp_path):
    async def scenario():
        engine, alerts, products = await _setup(tmp_path)
        await _new_alert(alerts, products, "gone", 25_000_000, 20_000_000)

        async def no_price(product):
            return None

        res = await PriceWatcherService(alerts=alerts, products=products, price_fetcher=no_price).check_alerts()
        await engine.dispose()
        return res[0]

    alert = asyncio.run(scenario())
    assert alert["status"] == "watching" and alert["lastCheckedAt"] and "Không đọc được giá" in alert["lastNote"]


def test_init_db_adds_new_alert_columns(tmp_path):
    async def scenario():
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'old.db'}")
        async with engine.begin() as conn:
            # Bảng price_alerts phiên bản cũ (chưa có product_id, status...)
            await conn.execute(
                text(
                    "CREATE TABLE price_alerts (id VARCHAR PRIMARY KEY, product_name VARCHAR NOT NULL, target_price FLOAT NOT NULL, "
                    "platform VARCHAR, user_email VARCHAR NOT NULL, created_at DATETIME)"
                )
            )
            from database import models  # noqa: F401

            await conn.run_sync(Base.metadata.create_all)
            await conn.run_sync(_add_missing_columns)
            cols = await conn.run_sync(lambda c: {col["name"] for col in inspect(c).get_columns("price_alerts")})
        await engine.dispose()
        return cols

    cols = asyncio.run(scenario())
    assert {"product_id", "status", "last_price", "lowest_price", "triggered_at", "pending_price"} <= cols


def _run_checks(tmp_path, readings, price=25_000_000, target=20_000_000, rounds=1, with_log=False):
    """
    readings: kết quả lần lượt cho mỗi lần đọc trang (số = giá còn hàng, dict = kết quả đầy đủ).
    Trả về (trạng thái alert sau mỗi vòng, lịch sử giá, lần đọc còn thừa[, nhật ký kiểm tra]).
    """

    async def scenario():
        engine, alerts, products = await _setup(tmp_path)
        factory = alerts.session_factory
        checks = PriceCheckRepository(factory) if with_log else None
        await _new_alert(alerts, products, "p", price, target)
        queue = list(readings)

        async def fake_price(product):
            if not queue:
                return None
            r = queue.pop(0)
            return r if isinstance(r, dict) else {"currentPrice": r, "inStock": True}

        watcher = PriceWatcherService(alerts=alerts, products=products, checks=checks, price_fetcher=fake_price)
        states = [(await watcher.check_alerts())[0] for _ in range(rounds)]
        history = [h["price"] for h in await products.get_price_history("p")]
        log = await checks.list(alert_id="alert-p") if checks else None
        await engine.dispose()
        return (states, history, queue, log) if with_log else (states, history, queue)

    return asyncio.run(scenario())


def test_anomalous_price_confirmed_by_next_reading(tmp_path):
    # Giá thật giảm mạnh (xả kho 25 tr -> 5 tr): lần 1 chờ xác nhận, lần 2 khớp -> chấp nhận, không kẹt mãi
    states, history, _ = _run_checks(tmp_path, [5_000_000, 5_050_000], target=4_000_000, rounds=2)
    first, second = states
    assert first["status"] == "watching" and first["lastPrice"] == 25_000_000 and first["pendingPrice"] == 5_000_000
    assert "xác nhận" in first["lastNote"]
    assert second["lastPrice"] == 5_050_000 and second["pendingPrice"] is None
    assert "Đã xác nhận giá mới" in second["lastNote"]
    assert history == [25_000_000, 5_050_000]


def test_anomalous_price_not_confirmed_stays_pending(tmp_path):
    states, history, _ = _run_checks(tmp_path, [2_000_000, 24_000_000], rounds=2)
    assert states[0]["pendingPrice"] == 2_000_000
    # Lần 2 đọc ra giá bình thường -> ghi nhận giá đó, bỏ trạng thái chờ
    assert states[1]["lastPrice"] == 24_000_000 and states[1]["pendingPrice"] is None
    assert history == [25_000_000, 24_000_000]


def test_big_drop_to_target_is_reread_before_triggering(tmp_path):
    # Giảm 40% xuống dưới mức mong muốn: đọc lại khớp -> báo đạt giá
    states, history, queue = _run_checks(tmp_path, [15_000_000, 15_000_000])
    assert states[0]["status"] == "triggered" and not queue
    assert history == [25_000_000, 15_000_000]


def test_big_drop_with_mismatching_reread_does_not_trigger(tmp_path):
    states, history, _ = _run_checks(tmp_path, [15_000_000, 24_500_000])
    alert = states[0]
    assert alert["status"] == "watching" and alert["lastPrice"] == 25_000_000
    assert alert["pendingPrice"] == 15_000_000 and "chưa báo đạt giá" in alert["lastNote"]
    assert history == [25_000_000]


def test_implausible_reading_is_ignored(tmp_path):
    # Laptop đọc ra 100.000 đ (giá dự phòng / trả góp) -> bỏ qua, không thành mốc chờ xác nhận
    states, history, _ = _run_checks(tmp_path, [100_000])
    assert states[0]["lastPrice"] == 25_000_000 and states[0]["pendingPrice"] is None
    assert "Bỏ qua giá" in states[0]["lastNote"]


def test_out_of_stock_does_not_trigger(tmp_path):
    # Giá dưới mức mong muốn nhưng sàn báo hết hàng -> không báo, không ghi mốc lịch sử
    states, history, _ = _run_checks(tmp_path, [{"currentPrice": 18_000_000, "inStock": False}])
    alert = states[0]
    assert alert["status"] == "watching" and alert["inStock"] is False and alert["lastPrice"] == 25_000_000
    assert "hết hàng" in alert["lastNote"]
    assert history == [25_000_000]


def test_out_of_stock_page_without_price(tmp_path):
    states, _, _ = _run_checks(tmp_path, [{"currentPrice": None, "inStock": False}])
    assert states[0]["inStock"] is False and "hết hàng" in states[0]["lastNote"]


def test_back_in_stock_triggers(tmp_path):
    states, _, _ = _run_checks(tmp_path, [{"currentPrice": 19_000_000, "inStock": False}, 19_000_000], rounds=2)
    assert states[0]["status"] == "watching"
    assert states[1]["status"] == "triggered" and states[1]["inStock"] is True


def test_price_checks_are_logged(tmp_path):
    readings = [{"currentPrice": 18_000_000, "inStock": False}, 2_000_000, 24_000_000, 19_000_000]
    states, _, _, log = _run_checks(tmp_path, readings, rounds=4, with_log=True)
    # Mới nhất trước
    assert [c["outcome"] for c in log] == ["triggered", "accepted", "pending", "out_of_stock"]
    assert log[-1]["inStock"] is False and log[-1]["price"] == 18_000_000 and log[-1]["latencyMs"] is not None
    assert states[-1]["status"] == "triggered"


def test_price_check_log_keeps_recent_entries(tmp_path):
    async def scenario():
        engine, alerts, _ = await _setup(tmp_path)
        repo = PriceCheckRepository(alerts.session_factory, keep_per_alert=3)
        for i in range(5):
            await repo.add({"alert_id": "a1", "user_id": "u1", "outcome": "accepted", "price": float(i)})
        await repo.add({"alert_id": "a2", "user_id": "u2", "outcome": "accepted", "price": 9.0})
        a1, u2 = await repo.list(alert_id="a1"), await repo.list(user_id="u2")
        await engine.dispose()
        return a1, u2

    a1, u2 = asyncio.run(scenario())
    assert [c["price"] for c in a1] == [4.0, 3.0, 2.0]
    assert [c["alertId"] for c in u2] == ["a2"]


def test_tiki_reading_uses_category_from_platform(tmp_path):
    # Tiki không có slug trong link: danh mục lấy từ mã sàn trả về cùng lần đọc giá
    async def scenario():
        engine, alerts, products = await _setup(tmp_path)
        await products.upsert_products(
            [
                {
                    "id": "tiki-1",
                    "name": "Dell Inspiron 15",
                    "platform": "tiki",
                    "platformName": "Tiki",
                    "currentPrice": 25_000_000,
                    "externalUrl": "https://tiki.vn/p1.html",
                }
            ]
        )
        await alerts.create(
            {
                "id": "alert-tiki",
                "product_id": "tiki-1",
                "product_name": "Dell Inspiron 15",
                "product_url": "https://tiki.vn/p1.html",
                "platform": "tiki",
                "platform_name": "Tiki",
                "target_price": 20_000_000,
                "initial_price": 25_000_000,
                "last_price": 25_000_000,
                "lowest_price": 25_000_000,
                "status": "watching",
            }
        )

        async def reading(product):
            return {"currentPrice": 150_000, "inStock": True, "sourceCategoryPath": "1/2/1846/8095"}

        watcher = PriceWatcherService(alerts=alerts, products=products, price_fetcher=reading)
        state = (await watcher.check_alerts())[0]
        await engine.dispose()
        return state

    state = asyncio.run(scenario())
    assert state["lastPrice"] == 25_000_000
    assert "Bỏ qua giá" in state["lastNote"]


def test_product_keeps_platform_category(tmp_path):
    async def scenario():
        engine, _, products = await _setup(tmp_path)
        item = {
            "id": "tiki-2",
            "name": "Dell Inspiron 15",
            "platform": "tiki",
            "platformName": "Tiki",
            "category": "phones",
            "currentPrice": 25_000_000,
            "externalUrl": "https://tiki.vn/p2.html",
        }
        first = (await products.upsert_products([{**item, "sourceCategoryPath": "1/2/1846/8095"}]))[0]
        # Lần cào sau không kèm mã: vẫn giữ mã đã lưu, không lấy nhãn theo câu hỏi tìm kiếm
        second = (await products.upsert_products([{**item, "currentPrice": 24_000_000}]))[0]
        await engine.dispose()
        return first, second

    first, second = asyncio.run(scenario())
    assert first["category"] == "laptops"
    assert second["category"] == "laptops" and second["sourceCategoryPath"] == "1/2/1846/8095"
