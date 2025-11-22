from __future__ import annotations

from pydantic import BaseModel


class UploadResponse(BaseModel):
    """Ответ после загрузки файла"""
    url: str
    path: str

