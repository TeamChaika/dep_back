from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.deps.supabase import get_supabase_client
from app.deps.auth import get_current_user_id, get_current_admin
from app.schemas.event import (
    EventCreate,
    EventUpdate,
    EventResponse,
)
from app.services.event_service import (
    create_event,
    get_event,
    get_event_public,
    list_events,
    update_event,
    delete_event,
)

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventResponse, status_code=201)
async def create(
    payload: EventCreate,
    client: Client = Depends(get_supabase_client),
    user_id: str = Depends(get_current_user_id),
) -> EventResponse:
    """Создать новое событие"""
    return await create_event(client=client, payload=payload, user_id=user_id)


@router.get("", response_model=list[EventResponse])
async def list_all(
    establishment_id: str | None = Query(None, description="Фильтр по заведению"),
    skip: int = Query(0, ge=0, description="Количество записей для пропуска"),
    limit: int = Query(100, ge=1, le=1000, description="Максимальное количество записей"),
    client: Client = Depends(get_supabase_client),
    user_id: str = Depends(get_current_user_id),
) -> list[EventResponse]:
    """Получить список событий пользователя"""
    return await list_events(
        client=client, establishment_id=establishment_id, user_id=user_id, skip=skip, limit=limit
    )


@router.get("/public/{event_id}", response_model=EventResponse)
async def get_public(
    event_id: str,
    client: Client = Depends(get_supabase_client),
) -> EventResponse:
    """Получить событие по ID (публичный доступ)"""
    return await get_event_public(client=client, event_id=event_id)


@router.get("/{event_id}", response_model=EventResponse)
async def get_by_id(
    event_id: str,
    client: Client = Depends(get_supabase_client),
    user_id: str = Depends(get_current_user_id),
) -> EventResponse:
    """Получить событие по ID (только свои события)"""
    return await get_event(client=client, event_id=event_id, user_id=user_id)


@router.put("/{event_id}", response_model=EventResponse)
async def update(
    event_id: str,
    payload: EventUpdate,
    client: Client = Depends(get_supabase_client),
    user_id: str = Depends(get_current_user_id),
) -> EventResponse:
    """Обновить событие (только свои события)"""
    return await update_event(
        client=client, event_id=event_id, payload=payload, user_id=user_id
    )


@router.delete("/{event_id}")
async def delete(
    event_id: str,
    client: Client = Depends(get_supabase_client),
    admin_id: str = Depends(get_current_admin),
) -> dict[str, str]:
    """Удалить событие (только для администраторов)"""
    return await delete_event(client=client, event_id=event_id)

