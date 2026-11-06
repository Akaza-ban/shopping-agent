from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from database.models import UserModel
from database.repositories import user_repository, user_to_dict, EmailAlreadyRegistered
from services.auth.service import (
    TOKEN_TTL_SECONDS, hash_password, login_throttle, new_token, normalize_email,
    validate_password, validate_registration, verify_password,
)
from src.auth import require_user
from src.config import settings

router = APIRouter(prefix="/auth", tags=["Auth"])

_DUMMY_HASH = hash_password("dummy-password-0")

USER_DATA_KEYS = {"conversations", "saved-products", "activities", "search-history", "preferences"}
MAX_USER_DATA_BYTES = 2 * 1024 * 1024


class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class UpdateProfileRequest(BaseModel):
    display_name: str


async def _issue_session(user: UserModel) -> dict:
    token, token_hash = new_token()
    await user_repository.create_token(user.id, token_hash, TOKEN_TTL_SECONDS)
    await user_repository.update_user(user.id, last_login_at=datetime.utcnow())
    return {"token": token, "user": user_to_dict(user)}


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest):
    errors = validate_registration(req.email, req.password, req.display_name)
    if errors:
        raise HTTPException(status_code=422, detail=" ".join(errors))
    email = normalize_email(req.email)
    admins = {normalize_email(e) for e in settings.ADMIN_EMAILS.split(",") if e.strip()}
    try:
        user = await user_repository.create_user(
            email=email,
            display_name=req.display_name.strip(),
            password_hash=hash_password(req.password),
            role="admin" if email in admins else "user",
        )
    except EmailAlreadyRegistered:
        raise HTTPException(status_code=409, detail="Email này đã được đăng ký.")
    return await _issue_session(user)


@router.post("/login")
async def login(req: LoginRequest):
    email = normalize_email(req.email)
    locked = login_throttle.locked_for(email)
    if locked:
        raise HTTPException(status_code=429, detail=f"Đăng nhập sai quá nhiều lần. Vui lòng thử lại sau {locked // 60 + 1} phút.")
    user = await user_repository.get_by_email(email)
    password_ok = verify_password(req.password, user.password_hash if user else _DUMMY_HASH)
    if not user or not password_ok:
        login_throttle.record_failure(email)
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng.")
    login_throttle.reset(email)
    return await _issue_session(user)


@router.post("/logout")
async def logout(request: Request, user: UserModel = Depends(require_user)):
    await user_repository.delete_token(request.state.token_hash)
    return {"ok": True}


@router.get("/me")
async def me(user: UserModel = Depends(require_user)):
    return user_to_dict(user)


@router.patch("/me")
async def update_profile(req: UpdateProfileRequest, user: UserModel = Depends(require_user)):
    name = req.display_name.strip()
    if not 2 <= len(name) <= 50:
        raise HTTPException(status_code=422, detail="Tên hiển thị cần từ 2 đến 50 ký tự.")
    updated = await user_repository.update_user(user.id, display_name=name)
    return user_to_dict(updated)


@router.post("/change-password")
async def change_password(req: ChangePasswordRequest, request: Request, user: UserModel = Depends(require_user)):
    if not verify_password(req.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không đúng.")
    errors = validate_password(req.new_password)
    if errors:
        raise HTTPException(status_code=422, detail=" ".join(errors))
    await user_repository.update_user(user.id, password_hash=hash_password(req.new_password))
    # Đăng xuất các thiết bị khác, giữ phiên hiện tại
    await user_repository.delete_user_tokens(user.id, keep_token_hash=request.state.token_hash)
    return {"ok": True}


@router.get("/me/data/{key}")
async def get_user_data(key: str, user: UserModel = Depends(require_user)):
    if key not in USER_DATA_KEYS:
        raise HTTPException(status_code=404, detail="Khóa dữ liệu không hợp lệ.")
    return {"key": key, "value": await user_repository.get_data(user.id, key)}


@router.put("/me/data/{key}")
async def put_user_data(key: str, request: Request, user: UserModel = Depends(require_user)):
    if key not in USER_DATA_KEYS:
        raise HTTPException(status_code=404, detail="Khóa dữ liệu không hợp lệ.")
    body = await request.body()
    if len(body) > MAX_USER_DATA_BYTES:
        raise HTTPException(status_code=413, detail="Dữ liệu quá lớn.")
    try:
        payload: Any = (await request.json()).get("value")
    except Exception:
        raise HTTPException(status_code=400, detail="Dữ liệu không phải JSON hợp lệ.")
    await user_repository.set_data(user.id, key, payload)
    return {"key": key, "saved": True}
