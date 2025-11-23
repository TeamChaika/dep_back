from __future__ import annotations

import logging
import uuid
from datetime import datetime
from fastapi import HTTPException, status
from supabase import Client

from app.core.database import db_execute
from app.schemas.deposit import (
    DepositCreate,
    DepositUpdate,
    DepositResponse,
    DepositByLinkResponse,
)

logger = logging.getLogger(__name__)


def generate_payment_link() -> str:
    """Генерирует уникальную ссылку для оплаты"""
    return f"deposit-{uuid.uuid4().hex}"


async def create_deposit(
    client: Client, payload: DepositCreate, user_id: str
) -> DepositResponse:
    """Создать новый депозит"""
    try:
        # Проверяем, что заведение принадлежит пользователю и не удалено
        establishment_response = await db_execute(
            client.table("establishments")
            .select("id")
            .eq("id", payload.establishment_id)
            .eq("owner_id", user_id)
            .eq("is_deleted", False)
        )
        
        if not establishment_response.data:
            raise ValueError("Establishment not found or access denied")
        
        # Если указано событие, проверяем что оно существует и принадлежит заведению
        if payload.event_id:
            event_response = await db_execute(
                client.table("events")
                .select("id, establishment_id")
                .eq("id", payload.event_id)
                .eq("establishment_id", payload.establishment_id)
                .eq("is_deleted", False)
            )
            
            if not event_response.data:
                raise ValueError("Event not found or does not belong to this establishment")
        
        payment_link = generate_payment_link()
        
        # Проверяем уникальность ссылки (маловероятно, но на всякий случай)
        # В асинхронном коде лучше сделать 1-2 попытки без while True, чтобы не заблокировать
        # Но пока оставим простую логику
        while True:
            check_response = await db_execute(
                client.table("deposits")
                .select("id")
                .eq("payment_link", payment_link)
            )
            if not check_response.data:
                break
            payment_link = generate_payment_link()
        
        data = {
            "establishment_id": payload.establishment_id,
            "event_id": payload.event_id,
            "guest_name": payload.guest_name,
            "guest_phone": payload.guest_phone,
            "guest_email": payload.guest_email,
            "amount": float(payload.amount),
            "visit_date": payload.visit_date.isoformat(),
            "visit_time": payload.visit_time.isoformat(),
            "payment_link": payment_link,
            "payment_status": "pending",
            "created_by": user_id,
            "is_deleted": False,
        }
        
        response = await db_execute(client.table("deposits").insert(data))
        
        if not response.data:
            raise ValueError("Failed to create deposit")
        
        return DepositResponse(**response.data[0])

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(f"Failed to create deposit: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create deposit: {exc}",
        ) from exc


async def get_deposit(
    client: Client, deposit_id: str, user_id: str
) -> DepositResponse:
    """Получить депозит по ID (только если пользователь является владельцем заведения)"""
    try:
        response = await db_execute(
            client.table("deposits")
            .select("*, establishments!inner(owner_id)")
            .eq("id", deposit_id)
            .eq("is_deleted", False)
        )
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deposit not found",
            )
        
        deposit_data = response.data[0]
        
        # Проверяем, что заведение принадлежит пользователю
        establishment = deposit_data.get("establishments")
        if not establishment or establishment.get("owner_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deposit not found or access denied",
            )
        
        # Удаляем вложенный объект establishments из результата
        if "establishments" in deposit_data:
            del deposit_data["establishments"]
            
        return DepositResponse(**deposit_data)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to get deposit: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get deposit: {exc}",
        ) from exc


async def get_deposit_by_link(
    client: Client, payment_link: str
) -> DepositByLinkResponse:
    """Получить депозит по ссылке оплаты (публичный доступ)"""
    try:
        response = await db_execute(
            client.table("deposits")
            .select("*")
            .eq("payment_link", payment_link)
            .eq("is_deleted", False)
        )
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deposit not found",
            )
        
        return DepositByLinkResponse(**response.data[0])

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to get deposit by link: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get deposit: {exc}",
        ) from exc


async def list_deposits(
    client: Client, establishment_id: str | None, event_id: str | None, user_id: str, skip: int = 0, limit: int = 100
) -> list[DepositResponse]:
    """Получить список депозитов (только для заведений пользователя)"""
    try:
        query = (
            client.table("deposits")
            .select("*, establishments!inner(owner_id)")
            .eq("establishments.owner_id", user_id)
            .eq("is_deleted", False)
            .order("created_at", desc=True)
        )
        
        if establishment_id:
            query = query.eq("establishment_id", establishment_id)
        
        if event_id:
            query = query.eq("event_id", event_id)
        
        response = await db_execute(query.range(skip, skip + limit - 1))
        
        results = response.data or []
        # Удаляем вложенные объекты establishments из результатов
        for item in results:
            if "establishments" in item:
                del item["establishments"]
        
        return [DepositResponse(**item) for item in results]

    except Exception as exc:
        logger.error(f"Failed to list deposits: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list deposits: {exc}",
        ) from exc


async def update_deposit(
    client: Client, deposit_id: str, payload: DepositUpdate, user_id: str
) -> DepositResponse:
    """Обновить депозит"""
    try:
        # Проверяем доступ к депозиту
        response = await db_execute(
            client.table("deposits")
            .select("*, establishments!inner(owner_id)")
            .eq("id", deposit_id)
            .eq("is_deleted", False)
        )
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deposit not found",
            )
        
        establishment = response.data[0].get("establishments")
        if not establishment or establishment.get("owner_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deposit not found or access denied",
            )
        
        # Собираем только переданные поля
        data = {}
        
        if payload.guest_name is not None:
            data["guest_name"] = payload.guest_name
        if payload.guest_phone is not None:
            data["guest_phone"] = payload.guest_phone
        if payload.guest_email is not None:
            data["guest_email"] = payload.guest_email
        if payload.amount is not None:
            data["amount"] = float(payload.amount)
        if payload.visit_date is not None:
            data["visit_date"] = payload.visit_date.isoformat()
        if payload.visit_time is not None:
            data["visit_time"] = payload.visit_time.isoformat()
        if payload.payment_status is not None:
            data["payment_status"] = payload.payment_status
            # Если статус меняется на "paid", устанавливаем paid_at
            if payload.payment_status == "paid":
                data["paid_at"] = datetime.now().isoformat()
            elif payload.payment_status != "paid":
                data["paid_at"] = None
        
        if not data:
            raise ValueError("No fields to update")
        
        update_response = await db_execute(
            client.table("deposits")
            .update(data)
            .eq("id", deposit_id)
            .eq("is_deleted", False)
        )
        
        if not update_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deposit not found, access denied, deleted, or update failed",
            )
        
        return DepositResponse(**update_response.data[0])

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to update deposit: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update deposit: {exc}",
        ) from exc


async def delete_deposit(client: Client, deposit_id: str) -> dict[str, str]:
    """Удалить депозит (только для администраторов - soft delete)"""
    try:
        # Помечаем депозит как удаленный вместо физического удаления
        response = await db_execute(
            client.table("deposits")
            .update({"is_deleted": True})
            .eq("id", deposit_id)
        )
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deposit not found",
            )
        
        return {"message": "Deposit marked as deleted successfully"}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to delete deposit: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete deposit: {exc}",
        ) from exc
