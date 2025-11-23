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
    supabase_anon_key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYW5vbiIsImlzcyI6InN1cGFiYXNlIiwiaWF0IjoxNzYzMTU0MDAwLCJleHAiOjE5MjA5MjA0MDB9.N9oeCHtulTdg9KT2PiV5oVjj2GQEVwf0XZF4Pd6urRI"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
