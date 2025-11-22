from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.deps.supabase import get_supabase_client
from app.deps.auth import get_current_user_id, get_current_admin
from app.schemas.ticket import (
    TicketCreate,
    TicketUpdate,
    TicketResponse,
    TicketByQRResponse,
    TicketCheckIn,
)
from app.services.ticket_service import (
    create_ticket,
    get_ticket,
    get_ticket_by_qr,
    check_in_ticket,
    list_tickets,
    update_ticket,
    delete_ticket,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketResponse, status_code=201)
async def create(
    payload: TicketCreate,
    client: Client = Depends(get_supabase_client),
    user_id: str = Depends(get_current_user_id),
) -> TicketResponse:
    """Создать новый билет"""
    return await create_ticket(client=client, payload=payload, user_id=user_id)


@router.get("", response_model=list[TicketResponse])
async def list_all(
    event_id: str | None = Query(None, description="Фильтр по событию"),
    skip: int = Query(0, ge=0, description="Количество записей для пропуска"),
    limit: int = Query(100, ge=1, le=1000, description="Максимальное количество записей"),
    client: Client = Depends(get_supabase_client),
    user_id: str = Depends(get_current_user_id),
) -> list[TicketResponse]:
    """Получить список билетов пользователя"""
    return await list_tickets(
        client=client, event_id=event_id, user_id=user_id, skip=skip, limit=limit
    )


@router.get("/by-qr/{qr_code}", response_model=TicketByQRResponse)
async def get_by_qr(
    qr_code: str,
    client: Client = Depends(get_supabase_client),
) -> TicketByQRResponse:
    """Получить билет по QR коду (публичный доступ)"""
    return await get_ticket_by_qr(client=client, qr_code=qr_code)


@router.post("/check-in/{qr_code}", response_model=TicketResponse)
async def check_in(
    qr_code: str,
    payload: TicketCheckIn,
    client: Client = Depends(get_supabase_client),
) -> TicketResponse:
    """Проверить билет (check-in) по QR коду (публичный доступ)"""
    return await check_in_ticket(client=client, qr_code=qr_code, payload=payload)


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_by_id(
    ticket_id: str,
    client: Client = Depends(get_supabase_client),
    user_id: str = Depends(get_current_user_id),
) -> TicketResponse:
    """Получить билет по ID (только свои билеты)"""
    return await get_ticket(client=client, ticket_id=ticket_id, user_id=user_id)


@router.put("/{ticket_id}", response_model=TicketResponse)
async def update(
    ticket_id: str,
    payload: TicketUpdate,
    client: Client = Depends(get_supabase_client),
    user_id: str = Depends(get_current_user_id),
) -> TicketResponse:
    """Обновить билет (только свои билеты)"""
    return await update_ticket(
        client=client, ticket_id=ticket_id, payload=payload, user_id=user_id
    )


@router.delete("/{ticket_id}")
async def delete(
    ticket_id: str,
    client: Client = Depends(get_supabase_client),
    admin_id: str = Depends(get_current_admin),
) -> dict[str, str]:
    """Удалить билет (только для администраторов)"""
    return await delete_ticket(client=client, ticket_id=ticket_id)

