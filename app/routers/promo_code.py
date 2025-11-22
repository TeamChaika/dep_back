from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.deps.supabase import get_supabase_client
from app.deps.auth import get_current_user_id, get_current_admin
from app.schemas.promo_code import (
    PromoCodeCreate,
    PromoCodeUpdate,
    PromoCodeResponse,
    PromoCodeValidate,
    PromoCodeValidationResponse,
)
from app.services.promo_code_service import (
    create_promo_code,
    get_promo_code,
    list_promo_codes,
    validate_promo_code,
    update_promo_code,
    delete_promo_code,
)

router = APIRouter(prefix="/promo-codes", tags=["promo-codes"])


@router.post("", response_model=PromoCodeResponse, status_code=201)
async def create(
    payload: PromoCodeCreate,
    client: Client = Depends(get_supabase_client),
    user_id: str = Depends(get_current_user_id),
) -> PromoCodeResponse:
    """Создать новый промокод"""
    return await create_promo_code(client=client, payload=payload, user_id=user_id)


@router.get("", response_model=list[PromoCodeResponse])
async def list_all(
    event_id: str | None = Query(None, description="Фильтр по событию"),
    skip: int = Query(0, ge=0, description="Количество записей для пропуска"),
    limit: int = Query(100, ge=1, le=1000, description="Максимальное количество записей"),
    client: Client = Depends(get_supabase_client),
    user_id: str = Depends(get_current_user_id),
) -> list[PromoCodeResponse]:
    """Получить список промокодов пользователя"""
    return await list_promo_codes(
        client=client, event_id=event_id, user_id=user_id, skip=skip, limit=limit
    )


@router.post("/validate", response_model=PromoCodeValidationResponse)
async def validate(
    payload: PromoCodeValidate,
    client: Client = Depends(get_supabase_client),
) -> PromoCodeValidationResponse:
    """Валидировать промокод (публичный доступ)"""
    return await validate_promo_code(client=client, payload=payload)


@router.get("/{promo_code_id}", response_model=PromoCodeResponse)
async def get_by_id(
    promo_code_id: str,
    client: Client = Depends(get_supabase_client),
    user_id: str = Depends(get_current_user_id),
) -> PromoCodeResponse:
    """Получить промокод по ID (только свои промокоды)"""
    return await get_promo_code(client=client, promo_code_id=promo_code_id, user_id=user_id)


@router.put("/{promo_code_id}", response_model=PromoCodeResponse)
async def update(
    promo_code_id: str,
    payload: PromoCodeUpdate,
    client: Client = Depends(get_supabase_client),
    user_id: str = Depends(get_current_user_id),
) -> PromoCodeResponse:
    """Обновить промокод (только свои промокоды)"""
    return await update_promo_code(
        client=client, promo_code_id=promo_code_id, payload=payload, user_id=user_id
    )


@router.delete("/{promo_code_id}")
async def delete(
    promo_code_id: str,
    client: Client = Depends(get_supabase_client),
    admin_id: str = Depends(get_current_admin),
) -> dict[str, str]:
    """Удалить промокод (только для администраторов)"""
    return await delete_promo_code(client=client, promo_code_id=promo_code_id)

