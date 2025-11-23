from __future__ import annotations

import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Deposits Tickets API"
    api_prefix: str = "/api/v1"
    
    # Supabase settings
    # Возвращаем дефолтные значения, чтобы приложение запускалось без .env
    # В продакшене эти значения должны быть переопределены через переменные окружения
    supabase_url: str = "https://s4.chaika.team"
    supabase_anon_key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYW5vbiIsImlzcyI6InN1cGFiYXNlIiwiaWF0IjoxNzYzNTg2MDAwLCJleHAiOjE5MjEzNTI0MDB9._OCmQ_QU6yItH90k4Ojw2K3eRRHOLtgEOCxIN3K5szQ"

    # S3 Storage settings
    s3_endpoint_url: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_bucket_name: str | None = None
    s3_region_name: str = "ru-1"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
