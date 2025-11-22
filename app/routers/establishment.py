from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.deps.supabase import get_supabase_client
from app.deps.auth import get_current_user_id, get_current_admin
from app.schemas.establishment import (
    EstablishmentCreate,
    EstablishmentUpdate,
    EstablishmentResponse,
)
from app.services.establishment_service import (
    create_establishment,
    get_establishment,
    list_establishments,
    update_establishment,
    delete_establishment,
)

router = APIRouter(prefix="/establishments", tags=["establishments"])


@router.post("", response_model=EstablishmentResponse, status_code=201)
async def create(
    payload: EstablishmentCreate,
    client: Client = Depends(get_supabase_client),
    user_id: str = Depends(get_current_user_id),
) -> EstablishmentResponse:
    """Создать новое заведение"""
    return await create_establishment(client=client, payload=payload, user_id=user_id)


@router.get("", response_model=list[EstablishmentResponse])
async def list_all(
    skip: int = Query(0, ge=0, description="Количество записей для пропуска"),
    limit: int = Query(100, ge=1, le=1000, description="Максимальное количество записей"),
    client: Client = Depends(get_supabase_client),
    user_id: str = Depends(get_current_user_id),
) -> list[EstablishmentResponse]:
    """Получить список заведений пользователя"""
    return await list_establishments(client=client, user_id=user_id, skip=skip, limit=limit)


@router.get("/{establishment_id}", response_model=EstablishmentResponse)
async def get_by_id(
    establishment_id: str,
    client: Client = Depends(get_supabase_client),
    user_id: str = Depends(get_current_user_id),
) -> EstablishmentResponse:
    """Получить заведение по ID (только свои заведения)"""
    return await get_establishment(client=client, establishment_id=establishment_id, user_id=user_id)


@router.put("/{establishment_id}", response_model=EstablishmentResponse)
async def update(
    establishment_id: str,
    payload: EstablishmentUpdate,
    client: Client = Depends(get_supabase_client),
    user_id: str = Depends(get_current_user_id),
) -> EstablishmentResponse:
    """Обновить заведение (только свои заведения)"""
    return await update_establishment(
        client=client, establishment_id=establishment_id, payload=payload, user_id=user_id
    )


@router.delete("/{establishment_id}")
async def delete(
    establishment_id: str,
    client: Client = Depends(get_supabase_client),
    admin_id: str = Depends(get_current_admin),
) -> dict[str, str]:
    """Удалить заведение (только для администраторов)"""
    return await delete_establishment(client=client, establishment_id=establishment_id)

