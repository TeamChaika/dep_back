from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import auth, establishment, event, upload, deposit, ticket, promo_code


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(auth.router, prefix=settings.api_prefix)
    application.include_router(establishment.router, prefix=settings.api_prefix)
    application.include_router(event.router, prefix=settings.api_prefix)
    application.include_router(upload.router, prefix=settings.api_prefix)
    application.include_router(deposit.router, prefix=settings.api_prefix)
    application.include_router(ticket.router, prefix=settings.api_prefix)
    application.include_router(promo_code.router, prefix=settings.api_prefix)
    return application


app = create_app()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

