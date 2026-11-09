"""API tài khoản và dữ liệu cá nhân. Logic nằm ở application/auth.py và application/user_data.py."""

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status

import application.auth as auth
import application.user_data as user_data
from database.models import UserModel
from src.dependencies.auth import require_user
from src.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UpdateProfileRequest,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest):
    return await auth.register(req.email, req.password, req.display_name)


@router.post("/login")
async def login(req: LoginRequest):
    return await auth.login(req.email, req.password)


@router.post("/logout")
async def logout(request: Request, user: UserModel = Depends(require_user)):
    return await auth.logout(request.state.token_hash)


@router.get("/me")
async def me(user: UserModel = Depends(require_user)):
    return auth.profile(user)


@router.patch("/me")
async def update_profile(req: UpdateProfileRequest, user: UserModel = Depends(require_user)):
    return await auth.update_profile(user, req.display_name)


@router.post("/change-password")
async def change_password(req: ChangePasswordRequest, request: Request, user: UserModel = Depends(require_user)):
    return await auth.change_password(user, req.current_password, req.new_password, request.state.token_hash)


@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest, background: BackgroundTasks):
    return await auth.forgot_password(req.email, schedule=background.add_task)


@router.get("/reset-password/check")
async def check_reset_link(token: str):
    return await auth.check_reset_link(token)


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest):
    return await auth.reset_password(req.token, req.new_password)


@router.get("/me/data/{key}")
async def get_user_data(key: str, user: UserModel = Depends(require_user)):
    return await user_data.get(user, key)


@router.put("/me/data/{key}")
async def put_user_data(key: str, request: Request, user: UserModel = Depends(require_user)):
    return await user_data.save(user, key, await request.body())
