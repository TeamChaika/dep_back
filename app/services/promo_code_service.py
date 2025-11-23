from __future__ import annotations

import logging
from datetime import datetime
from fastapi import HTTPException, status
from supabase import Client
from decimal import Decimal

from app.core.database import db_execute
from app.schemas.promo_code import (
    PromoCodeCreate,
    PromoCodeUpdate,
    PromoCodeResponse,
    PromoCodeValidate,
    PromoCodeValidationResponse,
)

logger = logging.getLogger(__name__)


async def create_promo_code(
    client: Client, payload: PromoCodeCreate, user_id: str
) -> PromoCodeResponse:
    """Создать новый промокод"""
    try:
        # Получаем событие
        event_response = await db_execute(
            client.table("events")
            .select("id, establishment_id")
            .eq("id", payload.event_id)
            .eq("is_deleted", False)
        )
        
        if not event_response.data:
            raise ValueError("Event not found")
        
        event = event_response.data[0]
        establishment_id = event.get("establishment_id")
        
        # Проверяем, что заведение принадлежит пользователю
        establishment_response = await db_execute(
            client.table("establishments")
            .select("id, owner_id")
            .eq("id", establishment_id)
            .eq("owner_id", user_id)
            .eq("is_deleted", False)
        )
        
        if not establishment_response.data:
            raise ValueError("Event not found or access denied")
        
        # Проверяем уникальность кода
        unique_response = await db_execute(
            client.table("promo_codes")
            .select("id")
            .eq("code", payload.code.upper())
            .eq("is_deleted", False)
        )
        
        if unique_response.data:
            raise ValueError("Promo code already exists")
        
        data = {
            "code": payload.code.upper(),
            "promo_type": payload.promo_type,
            "event_id": payload.event_id,
            "discount_value": float(payload.discount_value),
            "start_date": payload.start_date.isoformat(),
            "end_date": payload.end_date.isoformat(),
            "max_uses": payload.max_uses,
            "current_uses": 0,
            "is_active": payload.is_active,
            "is_deleted": False,
        }
        
        response = await db_execute(client.table("promo_codes").insert(data))
        
        if not response.data:
            raise ValueError("Failed to create promo code")
        
        return PromoCodeResponse(**response.data[0])

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(f"Failed to create promo code: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create promo code: {exc}",
        ) from exc


async def get_promo_code(
    client: Client, promo_code_id: str, user_id: str
) -> PromoCodeResponse:
    """Получить промокод по ID"""
    try:
        # Получаем промокод
        response = await db_execute(
            client.table("promo_codes")
            .select("*")
            .eq("id", promo_code_id)
            .eq("is_deleted", False)
        )
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Promo code not found",
            )
        
        promo_code = response.data[0]
        event_id = promo_code.get("event_id")
        
        # Проверяем доступ через событие
        event_response = await db_execute(
            client.table("events")
            .select("id, establishments!inner(owner_id)")
            .eq("id", event_id)
            .eq("is_deleted", False)
        )
        
        if not event_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found",
            )
        
        establishment = event_response.data[0].get("establishments")
        if not establishment or establishment.get("owner_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Promo code not found or access denied",
            )
        
        return PromoCodeResponse(**promo_code)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to get promo code: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get promo code: {exc}",
        ) from exc


async def list_promo_codes(
    client: Client, event_id: str | None, user_id: str, skip: int = 0, limit: int = 100
) -> list[PromoCodeResponse]:
    """Получить список промокодов"""
    try:
        # Сначала получаем события пользователя
        events_response = await db_execute(
            client.table("events")
            .select("id, establishments!inner(owner_id)")
            .eq("establishments.owner_id", user_id)
            .eq("is_deleted", False)
        )
        
        user_event_ids = [event["id"] for event in events_response.data]
        
        if not user_event_ids:
            return []
        
        # Теперь получаем промокоды для этих событий
        query = (
            client.table("promo_codes")
            .select("*")
            .in_("event_id", user_event_ids)
            .eq("is_deleted", False)
            .order("created_at", desc=True)
        )
        
        if event_id:
            # Проверяем, что событие принадлежит пользователю
            if event_id not in user_event_ids:
                return []
            query = query.eq("event_id", event_id)
        
        response = await db_execute(query.range(skip, skip + limit - 1))
        
        return [PromoCodeResponse(**item) for item in (response.data or [])]

    except Exception as exc:
        logger.error(f"Failed to list promo codes: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list promo codes: {exc}",
        ) from exc


async def validate_promo_code(
    client: Client, payload: PromoCodeValidate
) -> PromoCodeValidationResponse:
    """Валидировать промокод"""
    try:
        # Ищем активный промокод
        now = datetime.now().isoformat()
        response = await db_execute(
            client.table("promo_codes")
            .select("*")
            .eq("code", payload.code.upper())
            .eq("event_id", payload.event_id)
            .eq("is_active", True)
            .eq("is_deleted", False)
            .lte("start_date", now)
            .gte("end_date", now)
        )
        
        if not response.data:
            return PromoCodeValidationResponse(
                valid=False,
                discount_amount=0.0,
                final_price=float(payload.ticket_price),
                message="Промокод не найден или недействителен"
            )
        
        promo_code = response.data[0]
        
        # Проверяем лимит использований
        if promo_code.get("max_uses") is not None:
            if promo_code.get("current_uses", 0) >= promo_code.get("max_uses"):
                return PromoCodeValidationResponse(
                    valid=False,
                    discount_amount=0.0,
                    final_price=float(payload.ticket_price),
                    message="Промокод исчерпан"
                )
        
        # Рассчитываем скидку
        discount_amount = Decimal("0")
        if promo_code.get("promo_type") == "fixed":
            discount_amount = Decimal(str(promo_code.get("discount_value", 0)))
        elif promo_code.get("promo_type") == "percentage":
            percentage = Decimal(str(promo_code.get("discount_value", 0)))
            discount_amount = (payload.ticket_price * percentage) / Decimal("100")
        
        # Не даем скидку больше цены билета
        if discount_amount > payload.ticket_price:
            discount_amount = payload.ticket_price
        
        final_price = payload.ticket_price - discount_amount
        
        return PromoCodeValidationResponse(
            valid=True,
            discount_amount=float(discount_amount),
            final_price=float(final_price),
            promo_code_id=promo_code.get("id"),
            message="Промокод применен"
        )

    except Exception as exc:
        logger.error(f"Failed to validate promo code: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate promo code: {exc}",
        ) from exc


async def update_promo_code(
    client: Client, promo_code_id: str, payload: PromoCodeUpdate, user_id: str
) -> PromoCodeResponse:
    """Обновить промокод"""
    try:
        # Получаем промокод
        promo_response = await db_execute(
            client.table("promo_codes")
            .select("event_id")
            .eq("id", promo_code_id)
            .eq("is_deleted", False)
        )
        
        if not promo_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Promo code not found",
            )
        
        event_id = promo_response.data[0].get("event_id")
        
        # Проверяем доступ через событие
        event_response = await db_execute(
            client.table("events")
            .select("id, establishments!inner(owner_id)")
            .eq("id", event_id)
            .eq("is_deleted", False)
        )
        
        if not event_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found",
            )
        
        establishment = event_response.data[0].get("establishments")
        if not establishment or establishment.get("owner_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Promo code not found or access denied",
            )
        
        # Если код изменяется, проверяем уникальность
        if payload.code:
            unique_response = await db_execute(
                client.table("promo_codes")
                .select("id")
                .eq("code", payload.code.upper())
                .neq("id", promo_code_id)
                .eq("is_deleted", False)
            )
            
            if unique_response.data:
                raise ValueError("Promo code already exists")
        
        data = {}
        
        if payload.code is not None:
            data["code"] = payload.code.upper()
        if payload.discount_value is not None:
            data["discount_value"] = float(payload.discount_value)
        if payload.start_date is not None:
            data["start_date"] = payload.start_date.isoformat()
        if payload.end_date is not None:
            data["end_date"] = payload.end_date.isoformat()
        if payload.max_uses is not None:
            data["max_uses"] = payload.max_uses
        if payload.is_active is not None:
            data["is_active"] = payload.is_active
        
        if not data:
            raise ValueError("No fields to update")
        
        response = await db_execute(
            client.table("promo_codes")
            .update(data)
            .eq("id", promo_code_id)
            .eq("is_deleted", False)
        )
        
        if not response.data:
            raise ValueError("Promo code not found, access denied, deleted, or update failed")
        
        return PromoCodeResponse(**response.data[0])

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to update promo code: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update promo code: {exc}",
        ) from exc


async def delete_promo_code(client: Client, promo_code_id: str) -> dict[str, str]:
    """Удалить промокод (только для администраторов - soft delete)"""
    try:
        response = await db_execute(
            client.table("promo_codes")
            .update({"is_deleted": True})
            .eq("id", promo_code_id)
        )
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Promo code not found",
            )
        
        return {"message": "Promo code marked as deleted successfully"}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to delete promo code: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete promo code: {exc}",
        ) from exc
