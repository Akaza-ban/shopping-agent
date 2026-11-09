"""Bộ đếm tần suất (thời gian giả, không ngủ thật): đủ N lần thì chặn, hết cửa sổ thì cho gọi lại, mỗi người đếm riêng."""

from src.dependencies.rate_limit import RateLimiter


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_blocks_after_limit_and_reports_wait():
    clock = Clock()
    limiter = RateLimiter(((3, 60),), clock=clock)
    assert [limiter.hit("u1") for _ in range(3)] == [None, None, None]
    clock.now += 10
    assert limiter.hit("u1") == 51  # lần gọi đầu hết hạn sau 50 giây nữa (làm tròn lên)


def test_allows_again_after_window():
    clock = Clock()
    limiter = RateLimiter(((2, 60),), clock=clock)
    limiter.hit("u1"), limiter.hit("u1")
    assert limiter.hit("u1") is not None
    clock.now += 61
    assert limiter.hit("u1") is None


def test_blocked_calls_are_not_counted():
    clock = Clock()
    limiter = RateLimiter(((1, 60),), clock=clock)
    limiter.hit("u1")
    for _ in range(5):
        assert limiter.hit("u1") is not None
    clock.now += 61
    assert limiter.hit("u1") is None


def test_users_are_counted_separately():
    limiter = RateLimiter(((1, 60),), clock=Clock())
    assert limiter.hit("u1") is None
    assert limiter.hit("u1") is not None
    assert limiter.hit("u2") is None


def test_daily_limit_applies_after_minute_limit_resets():
    clock = Clock()
    limiter = RateLimiter(((2, 60), (3, 86400)), clock=clock)
    limiter.hit("u1"), limiter.hit("u1")
    clock.now += 61
    assert limiter.hit("u1") is None
    clock.now += 61
    wait = limiter.hit("u1")
    assert wait is not None and wait > 3600


def test_prune_removes_idle_users():
    clock = Clock()
    limiter = RateLimiter(((1, 60),), clock=clock)
    limiter.hit("u1")
    clock.now += 61
    limiter.hit("u2")
    limiter.prune()
    assert set(limiter._hits) == {"u2"}
