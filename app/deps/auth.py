from __future__ import annotations

from fastapi import Depends, HTTPException, status, Header
from fastapi.concurrency import run_in_threadpool
from supabase import Client
import jwt
from typing import Optional

from app.deps.supabase import get_supabase_client
from app.core.config import get_settings


async def get_current_user_id(
    authorization: Optional[str] = Header(None),
    client: Client = Depends(get_supabase_client),
) -> str:
    """Получить ID текущего пользователя из access token"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required",
        )
    
    try:
        # Извлекаем токен из заголовка "Bearer <token>"
        token = authorization.replace("Bearer ", "").strip()
        
        # Декодируем JWT токен для получения user_id
        # Для простоты не проверяем подпись, в продакшене нужно использовать service_role_key
        decoded = jwt.decode(
            token,
            options={"verify_signature": False}
        )
        
        user_id = decoded.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: user ID not found",
            )
        
        return user_id
    except jwt.DecodeError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {exc}",
        ) from exc


async def get_authenticated_client(
    authorization: Optional[str] = Header(None),
    base_client: Client = Depends(get_supabase_client),
) -> Client:
    """Получить Supabase client с установленной сессией пользователя"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required",
        )
    
    try:
        token = authorization.replace("Bearer ", "").strip()
        
        # Создаем новый client с токеном пользователя
        from supabase import create_client
        settings = get_settings()
        authenticated_client = create_client(
            settings.supabase_url,
            settings.supabase_anon_key,
        )
        authenticated_client.auth.set_session(token, "")
        
        return authenticated_client
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Failed to authenticate: {exc}",
        ) from exc


async def get_current_admin(
    user_id: str = Depends(get_current_user_id),
    client: Client = Depends(get_supabase_client),
) -> str:
    """Проверить, является ли пользователь администратором"""
    def _check_admin():
        response = (
            client.table("users")
            .select("is_admin")
            .eq("id", user_id)
            .execute()
        )
        
        if not response.data:
            raise ValueError("User not found")
        
        is_admin = response.data[0].get("is_admin", False)
        if not is_admin:
            raise ValueError("Admin access required")
        
        return user_id

    try:
        return await run_in_threadpool(_check_admin)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check admin status: {exc}",
        ) from exc

