"""Dependency xác thực cho các route FastAPI."""
from typing import Optional

from fastapi import Depends, HTTPException, Request, status

from database.models import UserModel
from database.repositories import user_repository
from services.auth.service import hash_token


def _extract_token(request: Request) -> Optional[str]:
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip() or None
    return request.query_params.get("access_token") or None


async def require_user(request: Request) -> UserModel:
    token = _extract_token(request)
    user = await user_repository.get_user_by_token(hash_token(token)) if token else None
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bạn cần đăng nhập để sử dụng chức năng này.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    request.state.token_hash = hash_token(token)
    return user


async def require_admin(user: UserModel = Depends(require_user)) -> UserModel:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chức năng này chỉ dành cho quản trị viên.")
    return user
