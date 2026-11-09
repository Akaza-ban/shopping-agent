"""Giới hạn tần suất gọi các API tốn tiền (LLM, cào sàn) theo từng người dùng.

Dùng trong route:  @router.post("", dependencies=[Depends(rate_limit("chat"))])
Muốn đổi mức giới hạn: sửa LIMITS bên dưới.

Bộ đếm nằm trong RAM của một process: chạy nhiều worker / nhiều máy thì mỗi nơi đếm riêng,
khi đó cần chuyển sang Redis.
"""

import time
from collections import deque
from collections.abc import Callable

from fastapi import Depends

from database.models import UserModel
from shared.exceptions import RateLimitedError
from src.dependencies.auth import require_user

MINUTE, DAY = 60, 24 * 3600

# tên bộ đếm -> các mức (số lần, trong bao nhiêu giây)
LIMITS: dict[str, tuple[tuple[int, int], ...]] = {
    "chat": ((10, MINUTE), (200, DAY)),  # POST /chat, POST + GET /chat/stream dùng chung
    "policy_lookup": ((20, MINUTE), (300, DAY)),
    "parse_link": ((10, MINUTE), (100, DAY)),
    "product_search": ((30, MINUTE),),
}


PRUNE_EVERY = 1000  # cứ bấy nhiêu lần gọi thì dọn key cũ một lần


class RateLimiter:
    """Cửa sổ trượt: mỗi key giữ mốc thời gian các lần gọi trong cửa sổ dài nhất."""

    def __init__(self, limits: tuple[tuple[int, int], ...], clock: Callable[[], float] = time.monotonic):
        self.limits = limits
        self.clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._calls = 0

    def hit(self, key: str) -> int | None:
        """Ghi nhận một lần gọi; vượt giới hạn thì không ghi và trả số giây phải chờ, ngược lại None."""
        self._calls += 1
        if self._calls % PRUNE_EVERY == 0:
            self.prune()
        now = self.clock()
        longest = max(window for _, window in self.limits)
        hits = self._hits.setdefault(key, deque())
        while hits and hits[0] <= now - longest:
            hits.popleft()
        for limit, window in self.limits:
            recent = [t for t in hits if t > now - window]
            if len(recent) >= limit:
                return max(1, int(recent[-limit] + window - now) + 1)
        hits.append(now)
        return None

    def prune(self) -> None:
        """Xóa các key không còn lần gọi nào trong cửa sổ (để bộ nhớ không phình theo số người dùng)."""
        now = self.clock()
        longest = max(window for _, window in self.limits)
        for key in [k for k, hits in self._hits.items() if not hits or hits[-1] <= now - longest]:
            del self._hits[key]

    def clear(self) -> None:
        self._hits.clear()


LIMITERS: dict[str, RateLimiter] = {name: RateLimiter(limits) for name, limits in LIMITS.items()}


def rate_limit(name: str):
    """Dependency: người dùng gọi quá mức `name` trong LIMITS -> RateLimitedError (429, có Retry-After)."""

    async def check(user: UserModel = Depends(require_user)) -> None:
        wait = LIMITERS[name].hit(user.id)
        if wait is not None:
            raise RateLimitedError(
                f"Bạn gửi yêu cầu quá nhanh, vui lòng thử lại sau {wait} giây.", headers={"Retry-After": str(wait)}
            )

    return check
