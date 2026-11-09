import json
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError

from database.repositories.serialization import iso
from shared.exceptions import EmailAlreadyRegistered

from ..connection import async_session
from ..errors import raises_database_error
from ..models import AuthTokenModel, PasswordResetModel, UserDataModel, UserModel


def user_to_dict(u: UserModel) -> dict[str, Any]:
    return {
        "id": u.id,
        "email": u.email,
        "displayName": u.display_name,
        "role": u.role,
        "createdAt": iso(u.created_at),
    }


@raises_database_error
class UserRepository:
    """Tài khoản, phiên đăng nhập và dữ liệu cá nhân của người dùng."""

    def __init__(self, session_factory=async_session):
        self.session_factory = session_factory

    async def create_user(self, email: str, display_name: str, password_hash: str, role: str = "user") -> UserModel:
        async with self.session_factory() as session:
            user = UserModel(
                id=f"user-{uuid.uuid4().hex[:12]}",
                email=email,
                display_name=display_name,
                password_hash=password_hash,
                role=role,
                created_at=datetime.utcnow(),
            )
            session.add(user)
            try:
                await session.commit()
            except IntegrityError as e:
                await session.rollback()
                raise EmailAlreadyRegistered(email) from e
            return user

    async def get_by_email(self, email: str) -> UserModel | None:
        async with self.session_factory() as session:
            res = await session.execute(select(UserModel).where(UserModel.email == email))
            return res.scalar_one_or_none()

    async def update_user(self, user_id: str, **fields: Any) -> UserModel | None:
        async with self.session_factory() as session:
            user = await session.get(UserModel, user_id)
            if not user:
                return None
            for key, value in fields.items():
                setattr(user, key, value)
            await session.commit()
            return user

    async def create_token(self, user_id: str, token_hash: str, ttl_seconds: int) -> None:
        async with self.session_factory() as session:
            now = datetime.utcnow()
            session.add(
                AuthTokenModel(
                    token_hash=token_hash,
                    user_id=user_id,
                    created_at=now,
                    expires_at=now + timedelta(seconds=ttl_seconds),
                )
            )
            await session.commit()

    async def get_user_by_token(self, token_hash: str) -> UserModel | None:
        async with self.session_factory() as session:
            token = await session.get(AuthTokenModel, token_hash)
            if not token:
                return None
            if token.expires_at < datetime.utcnow():
                await session.delete(token)
                await session.commit()
                return None
            return await session.get(UserModel, token.user_id)

    async def delete_token(self, token_hash: str) -> None:
        async with self.session_factory() as session:
            await session.execute(delete(AuthTokenModel).where(AuthTokenModel.token_hash == token_hash))
            await session.commit()

    # ------------------------------------------------------------------ đặt lại mật khẩu
    async def create_password_reset(self, user_id: str, token_hash: str, ttl_seconds: int) -> None:
        """Link mới thay cho mọi link cũ chưa dùng (vô hiệu chứ không xóa, để vẫn đếm được số link đã gửi trong giờ)."""
        async with self.session_factory() as session:
            now = datetime.utcnow()
            await session.execute(
                update(PasswordResetModel)
                .where(PasswordResetModel.user_id == user_id, PasswordResetModel.used_at.is_(None))
                .values(used_at=now)
            )
            session.add(
                PasswordResetModel(
                    token_hash=token_hash,
                    user_id=user_id,
                    created_at=now,
                    expires_at=now + timedelta(seconds=ttl_seconds),
                )
            )
            await session.commit()

    async def count_password_resets(self, user_id: str, since: datetime) -> int:
        async with self.session_factory() as session:
            stmt = (
                select(func.count())
                .select_from(PasswordResetModel)
                .where(PasswordResetModel.user_id == user_id, PasswordResetModel.created_at >= since)
            )
            return (await session.execute(stmt)).scalar() or 0

    async def user_for_password_reset(self, token_hash: str) -> UserModel | None:
        """Chủ tài khoản của link còn hiệu lực (chưa dùng, chưa hết hạn); None nếu link không dùng được."""
        async with self.session_factory() as session:
            reset = await session.get(PasswordResetModel, token_hash)
            if not reset or reset.used_at or reset.expires_at < datetime.utcnow():
                return None
            return await session.get(UserModel, reset.user_id)

    async def use_password_reset(self, token_hash: str, password_hash: str) -> UserModel | None:
        """Đổi mật khẩu bằng link (đánh dấu đã dùng ngay trong cùng giao dịch); None nếu link không dùng được."""
        async with self.session_factory() as session:
            reset = await session.get(PasswordResetModel, token_hash)
            if not reset or reset.used_at or reset.expires_at < datetime.utcnow():
                return None
            user = await session.get(UserModel, reset.user_id)
            if not user:
                return None
            reset.used_at = datetime.utcnow()
            user.password_hash = password_hash
            await session.commit()
            return user

    async def delete_user_tokens(self, user_id: str, keep_token_hash: str | None = None) -> None:
        """Đăng xuất mọi thiết bị (giữ lại phiên hiện tại nếu truyền vào)."""
        async with self.session_factory() as session:
            stmt = delete(AuthTokenModel).where(AuthTokenModel.user_id == user_id)
            if keep_token_hash:
                stmt = stmt.where(AuthTokenModel.token_hash != keep_token_hash)
            await session.execute(stmt)
            await session.commit()

    async def get_data(self, user_id: str, key: str) -> Any:
        async with self.session_factory() as session:
            res = await session.execute(
                select(UserDataModel).where(UserDataModel.user_id == user_id, UserDataModel.key == key)
            )
            row = res.scalar_one_or_none()
            return json.loads(row.value_json) if row else None

    async def set_data(self, user_id: str, key: str, value: Any) -> None:
        payload = json.dumps(value, ensure_ascii=False)
        async with self.session_factory() as session:
            res = await session.execute(
                select(UserDataModel).where(UserDataModel.user_id == user_id, UserDataModel.key == key)
            )
            row = res.scalar_one_or_none()
            if row:
                row.value_json = payload
                row.updated_at = datetime.utcnow()
            else:
                session.add(UserDataModel(user_id=user_id, key=key, value_json=payload, updated_at=datetime.utcnow()))
            await session.commit()


user_repository = UserRepository()
