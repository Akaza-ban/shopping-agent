"""Tài khoản: đăng ký, đăng nhập (khóa tạm khi sai nhiều lần), hồ sơ, đổi mật khẩu, quên / đặt lại mật khẩu.

Hàm băm mật khẩu, token, kiểm tra hợp lệ nằm ở services/auth/service.py; gửi email ở integrations/mail.py.
"""

from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import quote

from database.models import UserModel
from database.repositories import user_repository, user_to_dict
from integrations.mail import send_password_reset
from services.auth.service import (
    EMAIL_RE,
    TOKEN_TTL_SECONDS,
    hash_password,
    hash_token,
    login_throttle,
    new_token,
    normalize_email,
    validate_password,
    validate_registration,
    verify_password,
)
from shared.config import settings
from shared.exceptions import AuthenticationError, InvalidInputError, RateLimitedError, ValidationFailedError

# So khớp với hash giả khi email không tồn tại -> thời gian phản hồi như nhau, không lộ email nào đã đăng ký
_DUMMY_HASH = hash_password("dummy-password-0")

# Mỗi tài khoản tối đa 3 link đặt lại mật khẩu mỗi giờ (chống dùng tính năng để spam email người khác)
MAX_RESETS_PER_HOUR = 3
RESET_SENT_MESSAGE = (
    "Nếu email đã đăng ký, chúng tôi đã gửi link đặt lại mật khẩu. Vui lòng kiểm tra hộp thư (cả mục Spam)."
)
INVALID_RESET_LINK = "Link đặt lại mật khẩu không hợp lệ hoặc đã hết hạn. Vui lòng yêu cầu link mới."


async def _issue_session(user: UserModel) -> dict[str, Any]:
    token, token_hash = new_token()
    await user_repository.create_token(user.id, token_hash, TOKEN_TTL_SECONDS)
    await user_repository.update_user(user.id, last_login_at=datetime.utcnow())
    return {"token": token, "user": user_to_dict(user)}


def _check_password(password: str) -> None:
    errors = validate_password(password)
    if errors:
        raise ValidationFailedError(" ".join(errors))


async def register(email: str, password: str, display_name: str) -> dict[str, Any]:
    """Tạo tài khoản và đăng nhập luôn; email trong ADMIN_EMAILS thành quản trị viên."""
    errors = validate_registration(email, password, display_name)
    if errors:
        raise ValidationFailedError(" ".join(errors))
    email = normalize_email(email)
    admins = {normalize_email(e) for e in settings.ADMIN_EMAILS.split(",") if e.strip()}
    # Email đã có -> EmailAlreadyRegistered (409)
    user = await user_repository.create_user(
        email=email,
        display_name=display_name.strip(),
        password_hash=hash_password(password),
        role="admin" if email in admins else "user",
    )
    return await _issue_session(user)


async def login(email: str, password: str) -> dict[str, Any]:
    email = normalize_email(email)
    locked = login_throttle.locked_for(email)
    if locked:
        raise RateLimitedError(f"Đăng nhập sai quá nhiều lần. Vui lòng thử lại sau {locked // 60 + 1} phút.")
    user = await user_repository.get_by_email(email)
    password_ok = verify_password(password, user.password_hash if user else _DUMMY_HASH)
    if not user or not password_ok:
        login_throttle.record_failure(email)
        raise AuthenticationError("Email hoặc mật khẩu không đúng.")
    login_throttle.reset(email)
    return await _issue_session(user)


async def logout(token_hash: str) -> dict[str, Any]:
    await user_repository.delete_token(token_hash)
    return {"ok": True}


def profile(user: UserModel) -> dict[str, Any]:
    return user_to_dict(user)


async def update_profile(user: UserModel, display_name: str) -> dict[str, Any]:
    name = display_name.strip()
    if not 2 <= len(name) <= 50:
        raise ValidationFailedError("Tên hiển thị cần từ 2 đến 50 ký tự.")
    return user_to_dict(await user_repository.update_user(user.id, display_name=name))


async def change_password(
    user: UserModel, current_password: str, new_password: str, current_token_hash: str
) -> dict[str, Any]:
    """Đổi mật khẩu và đăng xuất các thiết bị khác, giữ phiên hiện tại."""
    if not verify_password(current_password, user.password_hash):
        raise InvalidInputError("Mật khẩu hiện tại không đúng.")
    _check_password(new_password)
    await user_repository.update_user(user.id, password_hash=hash_password(new_password))
    await user_repository.delete_user_tokens(user.id, keep_token_hash=current_token_hash)
    return {"ok": True}


async def forgot_password(email: str, schedule: Callable[..., None]) -> dict[str, Any]:
    """Gửi link đặt lại mật khẩu qua email.

    Luôn trả cùng một câu trả lời dù email có đăng ký hay không (không để lộ email nào đã có tài khoản).
    `schedule(fn, *args)` đưa việc gửi email ra chạy ngầm (route truyền BackgroundTasks.add_task)
    để thời gian phản hồi cũng như nhau.
    """
    email = normalize_email(email)
    if not EMAIL_RE.match(email):
        raise ValidationFailedError("Email không hợp lệ.")
    user = await user_repository.get_by_email(email)
    ttl = settings.PASSWORD_RESET_TTL_MINUTES
    recent = await user_repository.count_password_resets(user.id, datetime.utcnow() - timedelta(hours=1)) if user else 0
    if user and recent < MAX_RESETS_PER_HOUR:
        token, token_hash = new_token()
        await user_repository.create_password_reset(user.id, token_hash, ttl * 60)
        link = f"{settings.FRONTEND_URL.rstrip('/')}/?reset_token={quote(token)}"
        schedule(send_password_reset, user.email, user.display_name, link, ttl)
    return {"ok": True, "message": RESET_SENT_MESSAGE}


async def check_reset_link(token: str) -> dict[str, Any]:
    """Link còn dùng được không (để giao diện báo sớm link hết hạn trước khi người dùng nhập mật khẩu)."""
    user = await user_repository.user_for_password_reset(hash_token(token))
    return {"valid": user is not None, "email": user.email if user else None}


async def reset_password(token: str, new_password: str) -> dict[str, Any]:
    """Đặt mật khẩu mới bằng link trong email; đăng xuất mọi thiết bị để người đang giữ phiên cũ mất quyền truy cập."""
    _check_password(new_password)
    user = await user_repository.use_password_reset(hash_token(token), hash_password(new_password))
    if user is None:
        raise InvalidInputError(INVALID_RESET_LINK)
    await user_repository.delete_user_tokens(user.id)
    login_throttle.reset(user.email)
    return {"ok": True}
