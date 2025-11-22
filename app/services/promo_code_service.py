from __future__ import annotations

import logging
from datetime import datetime
from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from supabase import Client
from decimal import Decimal

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
    def _check_event():
        # Получаем событие
        event_response = (
            client.table("events")
            .select("id, establishment_id")
            .eq("id", payload.event_id)
            .eq("is_deleted", False)
            .execute()
        )
        
        if not event_response.data:
            raise ValueError("Event not found")
        
        event = event_response.data[0]
        establishment_id = event.get("establishment_id")
        
        # Проверяем, что заведение принадлежит пользователю
        establishment_response = (
            client.table("establishments")
            .select("id, owner_id")
            .eq("id", establishment_id)
            .eq("owner_id", user_id)
            .eq("is_deleted", False)
            .execute()
        )
        
        if not establishment_response.data:
            raise ValueError("Event not found or access denied")
        
        return True

    def _check_code_unique():
        # Проверяем уникальность кода
        response = (
            client.table("promo_codes")
            .select("id")
            .eq("code", payload.code.upper())
            .eq("is_deleted", False)
            .execute()
        )
        
        if response.data:
            raise ValueError("Promo code already exists")
        
        return True

    def _create():
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
        
        response = client.table("promo_codes").insert(data).execute()
        
        if not response.data:
            raise ValueError("Failed to create promo code")
        
        return response.data[0]

    try:
        await run_in_threadpool(_check_event)
        await run_in_threadpool(_check_code_unique)
        result = await run_in_threadpool(_create)
        return PromoCodeResponse(**result)
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
    def _get():
        # Получаем промокод
        response = (
            client.table("promo_codes")
            .select("*")
            .eq("id", promo_code_id)
            .eq("is_deleted", False)
            .execute()
        )
        
        if not response.data:
            raise ValueError("Promo code not found")
        
        promo_code = response.data[0]
        event_id = promo_code.get("event_id")
        
        # Проверяем доступ через событие
        event_response = (
            client.table("events")
            .select("id, establishments!inner(owner_id)")
            .eq("id", event_id)
            .eq("is_deleted", False)
            .execute()
        )
        
        if not event_response.data:
            raise ValueError("Event not found")
        
        establishment = event_response.data[0].get("establishments")
        if not establishment or establishment.get("owner_id") != user_id:
            raise ValueError("Promo code not found or access denied")
        
        return promo_code

    try:
        result = await run_in_threadpool(_get)
        return PromoCodeResponse(**result)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
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
    def _list():
        # Сначала получаем события пользователя
        events_response = (
            client.table("events")
            .select("id, establishments!inner(owner_id)")
            .eq("establishments.owner_id", user_id)
            .eq("is_deleted", False)
            .execute()
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
        
        response = query.range(skip, skip + limit - 1).execute()
        
        return response.data or []

    try:
        results = await run_in_threadpool(_list)
        return [PromoCodeResponse(**item) for item in results]
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
    def _validate():
        # Ищем активный промокод
        now = datetime.now().isoformat()
        response = (
            client.table("promo_codes")
            .select("*")
            .eq("code", payload.code.upper())
            .eq("event_id", payload.event_id)
            .eq("is_active", True)
            .eq("is_deleted", False)
            .lte("start_date", now)
            .gte("end_date", now)
            .execute()
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

    try:
        result = await run_in_threadpool(_validate)
        return result
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
    def _check_access():
        # Получаем промокод
        promo_response = (
            client.table("promo_codes")
            .select("event_id")
            .eq("id", promo_code_id)
            .eq("is_deleted", False)
            .execute()
        )
        
        if not promo_response.data:
            raise ValueError("Promo code not found")
        
        event_id = promo_response.data[0].get("event_id")
        
        # Проверяем доступ через событие
        event_response = (
            client.table("events")
            .select("id, establishments!inner(owner_id)")
            .eq("id", event_id)
            .eq("is_deleted", False)
            .execute()
        )
        
        if not event_response.data:
            raise ValueError("Event not found")
        
        establishment = event_response.data[0].get("establishments")
        if not establishment or establishment.get("owner_id") != user_id:
            raise ValueError("Promo code not found or access denied")
        
        return True

    def _check_code_unique():
        # Если код изменяется, проверяем уникальность
        if payload.code:
            response = (
                client.table("promo_codes")
                .select("id")
                .eq("code", payload.code.upper())
                .neq("id", promo_code_id)
                .eq("is_deleted", False)
                .execute()
            )
            
            if response.data:
                raise ValueError("Promo code already exists")
        
        return True

    def _update():
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
        
        response = (
            client.table("promo_codes")
            .update(data)
            .eq("id", promo_code_id)
            .eq("is_deleted", False)
            .execute()
        )
        
        if not response.data:
            raise ValueError("Promo code not found, access denied, deleted, or update failed")
        
        return response.data[0]

    try:
        await run_in_threadpool(_check_access)
        if payload.code:
            await run_in_threadpool(_check_code_unique)
        result = await run_in_threadpool(_update)
        return PromoCodeResponse(**result)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(f"Failed to update promo code: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update promo code: {exc}",
        ) from exc


async def delete_promo_code(client: Client, promo_code_id: str) -> dict[str, str]:
    """Удалить промокод (только для администраторов)"""
    def _delete():
        response = (
            client.table("promo_codes")
            .update({"is_deleted": True})
            .eq("id", promo_code_id)
            .execute()
        )
        
        if not response.data:
            raise ValueError("Promo code not found")
        
        return {"message": "Promo code marked as deleted successfully"}

    try:
        return await run_in_threadpool(_delete)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(f"Failed to delete promo code: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete promo code: {exc}",
        ) from exc
