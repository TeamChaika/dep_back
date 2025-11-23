from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile, File
from supabase import Client

from app.deps.auth import get_current_user_id, get_authenticated_client
from app.schemas.upload import UploadResponse
from app.services.upload_service import upload_event_poster

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/event-poster", response_model=UploadResponse)
async def upload_poster(
    file: UploadFile = File(...),
    client: Client = Depends(get_authenticated_client),
    user_id: str = Depends(get_current_user_id),
) -> UploadResponse:
    """Загрузить афишу события в Supabase Storage"""
    return await upload_event_poster(client=client, file=file, user_id=user_id)

