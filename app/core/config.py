from __future__ import annotations

from functools import lru_cache
import os
from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str
    api_prefix: str
    supabase_url: str
    supabase_anon_key: str


@lru_cache
def get_settings() -> Settings:
    env_supabase_url = os.getenv("SUPABASE_URL", "http://172.16.100.65:8000")
    env_supabase_key = os.getenv(
        "SUPABASE_ANON_KEY",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYW5vbiIsImlzcyI6InN1cGFiYXNlIiwiaWF0IjoxNzYzMTU0MDAwLCJleHAiOjE5MjA5MjA0MDB9.N9oeCHtulTdg9KT2PiV5oVjj2GQEVwf0XZF4Pd6urRI",
    )

    return Settings(
        app_name="Deposits Tickets API",
        api_prefix="/api/v1",
        supabase_url=env_supabase_url.rstrip("/"),
        supabase_anon_key=env_supabase_key,
    )

