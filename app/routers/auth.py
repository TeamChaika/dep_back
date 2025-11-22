from __future__ import annotations

from fastapi import APIRouter, Depends
from supabase import Client

from app.deps.supabase import get_supabase_client
from app.schemas.auth import (
    ChangeEmailRequest,
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RegisterRequest,
)
from app.services.auth_service import (
    change_email,
    change_password,
    confirm_password_reset,
    login_user,
    logout_user,
    register_user,
    request_password_reset,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=MessageResponse)
async def register(
    payload: RegisterRequest,
    client: Client = Depends(get_supabase_client),
) -> MessageResponse:
    return await register_user(client=client, payload=payload)


@router.post("/login", response_model=MessageResponse)
async def login(
    payload: LoginRequest,
    client: Client = Depends(get_supabase_client),
) -> MessageResponse:
    return await login_user(client=client, payload=payload)


@router.post("/request-password-reset", response_model=MessageResponse)
async def request_reset(
    payload: PasswordResetRequest,
    client: Client = Depends(get_supabase_client),
) -> MessageResponse:
    return await request_password_reset(client=client, payload=payload)


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    payload: PasswordResetConfirmRequest,
    client: Client = Depends(get_supabase_client),
) -> MessageResponse:
    return await confirm_password_reset(client=client, payload=payload)


@router.post("/change-password", response_model=MessageResponse)
async def change_password_route(
    payload: ChangePasswordRequest,
    client: Client = Depends(get_supabase_client),
) -> MessageResponse:
    return await change_password(client=client, payload=payload)


@router.post("/change-email", response_model=MessageResponse)
async def change_email_route(
    payload: ChangeEmailRequest,
    client: Client = Depends(get_supabase_client),
) -> MessageResponse:
    return await change_email(client=client, payload=payload)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    payload: LogoutRequest,
    client: Client = Depends(get_supabase_client),
) -> MessageResponse:
    return await logout_user(client=client, access_token=payload.access_token)

