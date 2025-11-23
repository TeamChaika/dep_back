from __future__ import annotations

import io
import logging
import uuid
from datetime import datetime

import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, status, UploadFile
from supabase import Client

from app.core.database import db_execute
from app.schemas.upload import UploadResponse
from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def upload_event_poster(
    client: Client, file: UploadFile, user_id: str
) -> UploadResponse:
    """Загрузить афишу события в S3 хранилище"""
    
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
    
    def _upload_s3():
        settings = get_settings()
        
        if not settings.s3_endpoint_url or not settings.s3_access_key or not settings.s3_secret_key or not settings.s3_bucket_name:
            raise ValueError("S3 configuration is missing (endpoint, access_key, secret_key, or bucket_name)")

        # Генерируем уникальное имя файла
        file_extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{user_id}_{timestamp}_{uuid.uuid4().hex[:8]}.{file_extension}"
        
        # Инициализируем S3 клиент
        s3_client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region_name,
            verify=True, # Включаем проверку SSL для публичного провайдера
            use_ssl=True,
        )

        try:
            # Загружаем файл
            file_obj = io.BytesIO(file_content)
            s3_client.upload_fileobj(
                file_obj,
                settings.s3_bucket_name,
                unique_filename,
                ExtraArgs={
                    "ContentType": file.content_type,
                    "ACL": "public-read",  # Делаем файл публичным
                },
            )
            
            # Формируем публичный URL
            # Обычно это endpoint_url/bucket_name/filename
            # Если endpoint без пути, добавляем bucket name
            base_url = settings.s3_endpoint_url.rstrip("/")
            public_url = f"{base_url}/{settings.s3_bucket_name}/{unique_filename}"
            
            return UploadResponse(url=public_url, path=unique_filename)
            
        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            raise ValueError(f"Failed to upload file to S3: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error during S3 upload: {e}")
            raise ValueError(f"Unexpected error: {e}") from e
    
    try:
        # Используем db_execute для запуска синхронного вызова boto3 в threadpool
        return await db_execute(_upload_s3)
    except ValueError as exc:
        # Пробрасываем понятные ошибки конфигурации или загрузки
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if "S3 configuration is missing" in str(exc):
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        
        raise HTTPException(
            status_code=status_code,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(f"Failed to upload event poster: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {exc}",
        ) from exc
