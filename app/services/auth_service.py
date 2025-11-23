from __future__ import annotations

import logging
from typing import Any

import requests
from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from supabase import Client, create_client

from app.core.config import get_settings
from app.core.database import db_execute
from app.schemas.auth import (
    ChangeEmailRequest,
    ChangePasswordRequest,
    LoginRequest,
    MessageResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RegisterRequest,
)

logger = logging.getLogger(__name__)


async def register_user(client: Client, payload: RegisterRequest) -> MessageResponse:
    try:
        # Supabase GoTrue calls are synchronous
        # We can use db_execute if it supports callables, or just wrapper
        def _sign_up():
            return client.auth.sign_up({"email": payload.email, "password": payload.password})
        
        response = await db_execute(_sign_up)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {exc}",
        ) from exc

    # Get user ID from the response
    if not response.user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User creation failed: no user returned",
        )

    user_id = response.user.id
    user_email = response.user.email or payload.email

    # Create user record in users table
    try:
        await db_execute(
            client.table("users").insert({
                "id": user_id,
                "email": user_email,
                "phone": payload.phone,
                "first_name": payload.first_name,
                "last_name": payload.last_name,
                "is_deleted": False,
            })
        )
    except Exception as exc:
        # Log the error but don't fail registration if user record creation fails
        logger.error(f"Failed to create user record in users table for user {user_id}: {exc}")

    token = response.session.access_token if response.session else None
    return MessageResponse(message="Registration successful", access_token=token)


async def login_user(client: Client, payload: LoginRequest) -> MessageResponse:
    try:
        def _sign_in():
            return client.auth.sign_in_with_password(
                {"email": payload.email, "password": payload.password}
            )
        response = await db_execute(_sign_in)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login failed: {exc}",
        ) from exc

    if not response.session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    # Проверяем, не удален ли аккаунт
    user_id = response.user.id
    try:
        user_response = await db_execute(
            client.table("users").select("is_deleted").eq("id", user_id)
        )
        if user_response.data and user_response.data[0].get("is_deleted", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account has been deleted. Please contact support.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        # Если не удалось проверить, логируем, но не блокируем вход
        logger.warning(f"Failed to check user deletion status: {exc}")

    return MessageResponse(
        message="Login successful",
        access_token=response.session.access_token,
    )


async def request_password_reset(
    client: Client, payload: PasswordResetRequest
) -> MessageResponse:
    try:
        def _reset():
            return client.auth.reset_password_email(payload.email)
        await db_execute(_reset)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password reset failed: {exc}",
        ) from exc

    return MessageResponse(message="Password reset email sent")


async def _update_user_with_token(
    access_token: str,
    attributes: dict[str, Any],
) -> None:
    settings = get_settings()

    def _send_request():
        return requests.put(
            f"{settings.supabase_url}/auth/v1/user",
            headers={
                "apikey": settings.supabase_anon_key,
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json=attributes,
            timeout=10,
        )

    response = await run_in_threadpool(_send_request)

    if response.status_code >= 400:
        detail = response.json().get("message", "Supabase user update failed")
        raise HTTPException(
            status_code=response.status_code,
            detail=detail,
        )


async def confirm_password_reset(
    client: Client, payload: PasswordResetConfirmRequest
) -> MessageResponse:
    if not payload.recovery_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="recovery_token is required to reset password",
        )

    try:
        def _verify_otp():
            verify_response = client.auth.verify_otp(
                {
                    "token": payload.recovery_token,
                    "type": "recovery",
                }
            )
            if not verify_response.session:
                raise ValueError("Invalid or expired recovery token")
            return verify_response.session.access_token

        access_token = await db_execute(_verify_otp)
        
        await _update_user_with_token(
            access_token=access_token,
            attributes={"password": payload.new_password},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password reset failed: {exc}",
        ) from exc

    return MessageResponse(message="Password updated successfully")


async def change_password(client: Client, payload: ChangePasswordRequest) -> MessageResponse:
    if not payload.access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="access_token is required to change password",
        )

    try:
        await _update_user_with_token(
            access_token=payload.access_token,
            attributes={"password": payload.new_password},
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Change password failed: {exc}",
        ) from exc

    return MessageResponse(message="Password changed")


async def change_email(client: Client, payload: ChangeEmailRequest) -> MessageResponse:
    if not payload.access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="access_token is required to change email",
        )

    try:
        await _update_user_with_token(
            access_token=payload.access_token,
            attributes={"email": payload.new_email},
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Change email failed: {exc}",
        ) from exc

    return MessageResponse(message="Email change requested")


async def logout_user(client: Client, access_token: str | None = None) -> MessageResponse:
    def _sign_out():
        if access_token:
            settings = get_settings()
            session_client = create_client(
                settings.supabase_url,
                settings.supabase_anon_key,
            )
            try:
                session_client.auth.set_session(access_token, "")
                session_client.auth.sign_out()
            except Exception:
                pass
        return None

    try:
        await db_execute(_sign_out)
    except Exception:
        pass

    return MessageResponse(message="Logged out successfully")
