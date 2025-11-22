from __future__ import annotations

import logging
import uuid
from datetime import datetime
from fastapi import HTTPException, status, UploadFile
from fastapi.concurrency import run_in_threadpool
from supabase import Client

from app.schemas.upload import UploadResponse
from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def upload_event_poster(
    client: Client, file: UploadFile, user_id: str
) -> UploadResponse:
    """Загрузить афишу события в Supabase Storage"""
    
    # Проверяем тип файла
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}",
        )
    
    # Проверяем размер файла (максимум 10MB)
    max_size = 10 * 1024 * 1024  # 10MB
    file_content = await file.read()
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds maximum allowed size (10MB)",
        )
    
    def _upload():
        # Генерируем уникальное имя файла
        file_extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{user_id}_{timestamp}_{uuid.uuid4().hex[:8]}.{file_extension}"
        file_path = unique_filename  # Путь относительно bucket
        
        try:
            # Загружаем файл в Supabase Storage (bucket: event-posters)
            storage_response = client.storage.from_("event-posters").upload(
                file_path,
                file_content,
                file_options={"content-type": file.content_type, "upsert": False}
            )
            
            # Получаем публичный URL
            settings = get_settings()
            public_url = f"{settings.supabase_url}/storage/v1/object/public/event-posters/{file_path}"
            
            return UploadResponse(url=public_url, path=file_path)
        except Exception as exc:
            logger.error(f"Failed to upload file to Supabase Storage: {exc}")
            raise ValueError(f"Failed to upload file: {exc}") from exc
    
    try:
        return await run_in_threadpool(_upload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(f"Failed to upload event poster: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {exc}",
        ) from exc

