from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Deposits Tickets API"
    api_prefix: str = "/api/v1"
    
    # Supabase settings - required from environment
    # Делаем их опциональными для локальной разработки или предоставляем дефолтные значения
    # Но лучше требовать их наличия
    supabase_url: str
    supabase_anon_key: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
