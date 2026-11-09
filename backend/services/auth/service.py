"""Xác thực người dùng: băm mật khẩu (bcrypt), kiểm tra dữ liệu đăng ký, tạo / băm token phiên, giới hạn số lần đăng nhập sai liên tiếp."""

import hashlib
import re
import secrets
import time

import bcrypt

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_BYTES = 72  # giới hạn của bcrypt
TOKEN_TTL_SECONDS = 30 * 24 * 3600

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 5 * 60


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def validate_registration(email: str, password: str, display_name: str) -> list[str]:
    """Trả về danh sách lỗi (rỗng = hợp lệ)."""
    errors = []
    if not EMAIL_RE.match(normalize_email(email)):
        errors.append("Email không hợp lệ.")
    name = (display_name or "").strip()
    if not 2 <= len(name) <= 50:
        errors.append("Tên hiển thị cần từ 2 đến 50 ký tự.")
    errors.extend(validate_password(password))
    return errors


def validate_password(password: str) -> list[str]:
    errors = []
    if len(password or "") < MIN_PASSWORD_LENGTH:
        errors.append(f"Mật khẩu cần ít nhất {MIN_PASSWORD_LENGTH} ký tự.")
    elif len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        errors.append("Mật khẩu quá dài (tối đa 72 byte).")
    if password and not (re.search(r"[A-Za-z]", password) and re.search(r"\d", password)):
        errors.append("Mật khẩu cần có cả chữ và số.")
    return errors


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:
        return False


def new_token() -> tuple[str, str]:
    """(token gửi cho trình duyệt, SHA-256 của token để lưu DB)."""
    token = secrets.token_urlsafe(32)
    return token, hash_token(token)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class LoginThrottle:
    """Đếm số lần đăng nhập sai liên tiếp theo email; khóa tạm khi vượt ngưỡng."""

    def __init__(self, max_attempts: int = MAX_FAILED_ATTEMPTS, lockout_seconds: int = LOCKOUT_SECONDS):
        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_seconds
        self._failures: dict[str, tuple[int, float]] = {}

    def locked_for(self, email: str) -> int | None:
        """Số giây còn bị khóa, hoặc None nếu không bị khóa."""
        count, since = self._failures.get(email, (0, 0.0))
        if count < self.max_attempts:
            return None
        remaining = int(self.lockout_seconds - (time.time() - since))
        if remaining <= 0:
            self._failures.pop(email, None)
            return None
        return remaining

    def record_failure(self, email: str) -> None:
        count, _ = self._failures.get(email, (0, 0.0))
        self._failures[email] = (count + 1, time.time())

    def reset(self, email: str) -> None:
        self._failures.pop(email, None)


login_throttle = LoginThrottle()
