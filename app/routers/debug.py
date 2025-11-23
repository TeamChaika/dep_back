from __future__ import annotations

from fastapi import APIRouter
from app.core.config import get_settings

router = APIRouter(tags=["debug"])

@router.get("/debug/config")
async def debug_config():
    settings = get_settings()
    return {
        "supabase_url": settings.supabase_url,
        # Показываем только первые 10 символов ключа для безопасности
        "supabase_anon_key_prefix": settings.supabase_anon_key[:10] if settings.supabase_anon_key else None
    }

