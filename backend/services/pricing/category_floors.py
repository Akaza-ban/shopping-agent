"""Giá tối thiểu hợp lý của từng ngành hàng, tính từ giá thật trong kho (thay cho con số viết tay)."""

import logging
import time
from collections.abc import Iterable

from database.repositories import product_repository
from shared.exceptions import DatabaseError

logger = logging.getLogger("category_floors")

FLOOR_PERCENTILE = 0.05
FLOOR_FACTOR = 0.15
MIN_SAMPLES = 30
REFRESH_SECONDS = 6 * 3600


def compute_floors(rows: Iterable[tuple[str, float]]) -> dict[str, float]:
    """(ngành hàng, giá) -> {ngành hàng: giá tối thiểu}."""
    prices: dict[str, list] = {}
    for category, price in rows:
        if category and category != "other" and price and price > 0:
            prices.setdefault(category, []).append(float(price))
    floors = {}
    for category, values in prices.items():
        if len(values) < MIN_SAMPLES:
            continue
        values.sort()
        floors[category] = round(values[int(FLOOR_PERCENTILE * len(values))] * FLOOR_FACTOR, -3)
    return floors


class CategoryFloors:
    def __init__(self):
        self._floors: dict[str, float] = {}
        self._updated_at = 0.0

    def get(self, category: str | None) -> float | None:
        return self._floors.get(category or "")

    def set(self, floors: dict[str, float]) -> None:
        self._floors = dict(floors)
        self._updated_at = time.time()

    async def refresh(self, force: bool = False) -> None:
        """Tính lại từ bảng products; mặc định chỉ khi đã quá REFRESH_SECONDS."""
        if not force and time.time() - self._updated_at < REFRESH_SECONDS:
            return
        try:
            rows = await product_repository.category_prices()
        except DatabaseError as e:
            logger.warning(f"Không tính được ngưỡng giá theo ngành: {e}")
            return
        self.set(compute_floors(rows))
        logger.info("Ngưỡng giá theo ngành: " + ", ".join(f"{c} {v:,.0f} đ" for c, v in sorted(self._floors.items())))


category_floors = CategoryFloors()
