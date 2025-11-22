from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.deps.supabase import get_supabase_client
from app.deps.auth import get_current_user_id, get_current_admin
from app.schemas.deposit import (
    DepositCreate,
    DepositUpdate,
    DepositResponse,
    DepositByLinkResponse,
)
from app.services.deposit_service import (
    create_deposit,
    get_deposit,
    get_deposit_by_link,
    list_deposits,
    update_deposit,
    delete_deposit,
)

router = APIRouter(prefix="/deposits", tags=["deposits"])


@router.post("", response_model=DepositResponse, status_code=201)
async def create(
    payload: DepositCreate,
    client: Client = Depends(get_supabase_client),
    user_id: str = Depends(get_current_user_id),
) -> DepositResponse:
    """Создать новый депозит"""
    return await create_deposit(client=client, payload=payload, user_id=user_id)


@router.get("", response_model=list[DepositResponse])
async def list_all(
    establishment_id: str | None = Query(None, description="Фильтр по заведению"),
    event_id: str | None = Query(None, description="Фильтр по событию"),
    skip: int = Query(0, ge=0, description="Количество записей для пропуска"),
    limit: int = Query(100, ge=1, le=1000, description="Максимальное количество записей"),
    client: Client = Depends(get_supabase_client),
    user_id: str = Depends(get_current_user_id),
) -> list[DepositResponse]:
    """Получить список депозитов пользователя"""
    return await list_deposits(
        client=client,
        establishment_id=establishment_id,
        event_id=event_id,
        user_id=user_id,
        skip=skip,
        limit=limit,
    )


@router.get("/by-link/{payment_link}", response_model=DepositByLinkResponse)
async def get_by_link(
    payment_link: str,
    client: Client = Depends(get_supabase_client),
) -> DepositByLinkResponse:
    """Получить депозит по ссылке оплаты (публичный доступ)"""
    return await get_deposit_by_link(client=client, payment_link=payment_link)


@router.get("/{deposit_id}", response_model=DepositResponse)
async def get_by_id(
    deposit_id: str,
    client: Client = Depends(get_supabase_client),
    user_id: str = Depends(get_current_user_id),
) -> DepositResponse:
    """Получить депозит по ID (только свои депозиты)"""
    return await get_deposit(client=client, deposit_id=deposit_id, user_id=user_id)


@router.put("/{deposit_id}", response_model=DepositResponse)
async def update(
    deposit_id: str,
    payload: DepositUpdate,
    client: Client = Depends(get_supabase_client),
    user_id: str = Depends(get_current_user_id),
) -> DepositResponse:
    """Обновить депозит (только свои депозиты)"""
    return await update_deposit(
        client=client, deposit_id=deposit_id, payload=payload, user_id=user_id
    )


@router.delete("/{deposit_id}")
async def delete(
    deposit_id: str,
    client: Client = Depends(get_supabase_client),
    admin_id: str = Depends(get_current_admin),
) -> dict[str, str]:
    """Удалить депозит (только для администраторов)"""
    return await delete_deposit(client=client, deposit_id=deposit_id)

