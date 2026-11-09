"""Gửi email qua SMTP (cấu hình SMTP_* trong .env). Chưa cấu hình: môi trường development ghi link ra log để thử."""

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from shared.config import settings

logger = logging.getLogger("mailer")


def smtp_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_FROM)


def _send(to: str, subject: str, text: str, html: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    if settings.SMTP_PORT == 465:
        server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20)
    else:
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20)
        server.starttls()
    with server:
        if settings.SMTP_USERNAME:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(msg)


async def send_password_reset(to: str, name: str, link: str, ttl_minutes: int) -> bool:
    """Gửi link đặt lại mật khẩu; True nếu đã gửi (hoặc đã ghi ra log ở development)."""
    if not smtp_configured():
        if settings.ENVIRONMENT == "development":
            logger.warning(f"[DEV] Chưa cấu hình SMTP - link đặt lại mật khẩu cho {to}: {link}")
            return True
        logger.error("Chưa cấu hình SMTP (SMTP_HOST, SMTP_FROM) nên không gửi được email đặt lại mật khẩu.")
        return False
    subject = "Shopping AI - Đặt lại mật khẩu"
    text = (
        f"Xin chào {name},\n\nBạn (hoặc ai đó) vừa yêu cầu đặt lại mật khẩu tài khoản Shopping AI.\n"
        f"Mở link sau để đặt mật khẩu mới (hiệu lực {ttl_minutes} phút, dùng được một lần):\n{link}\n\n"
        "Nếu bạn không yêu cầu, hãy bỏ qua email này; mật khẩu hiện tại vẫn giữ nguyên."
    )
    html = (
        f"<p>Xin chào {_escape(name)},</p><p>Bạn (hoặc ai đó) vừa yêu cầu đặt lại mật khẩu tài khoản Shopping AI.</p>"
        f'<p><a href="{_escape(link)}" style="display:inline-block;padding:10px 18px;background:#1c1917;color:#fffbeb;'
        f'border-radius:10px;text-decoration:none;font-weight:600">Đặt mật khẩu mới</a></p>'
        f"<p>Link có hiệu lực {ttl_minutes} phút và chỉ dùng được một lần.</p>"
        "<p>Nếu bạn không yêu cầu, hãy bỏ qua email này; mật khẩu hiện tại vẫn giữ nguyên.</p>"
    )
    try:
        await asyncio.to_thread(_send, to, subject, text, html)
        return True
    except (smtplib.SMTPException, OSError) as e:
        logger.error(f"Gửi email đặt lại mật khẩu thất bại: {type(e).__name__}: {e}")
        return False


def _escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
