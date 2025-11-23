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
    s3_endpoint_url: str | None = "https://s3.chaika.team"
    s3_access_key: str | None = "5DOKPHK6O1RHJ47OQNUI"
    s3_secret_key: str | None = "MnJYMdO0tvA1UhLIyVHT3luthtNkptvCoyrKAgjC"
    s3_bucket_name: str = "359ffbe7-3f866801-eeba-4f2b-b4a5-2fad15ff3500"
    s3_region_name: str = "ru-1"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
