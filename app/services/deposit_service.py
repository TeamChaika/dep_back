from __future__ import annotations

import logging
import uuid
from datetime import datetime
from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from supabase import Client

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
    def _check_establishment():
        # Проверяем, что заведение принадлежит пользователю и не удалено
        response = (
            client.table("establishments")
            .select("id")
            .eq("id", payload.establishment_id)
            .eq("owner_id", user_id)
            .eq("is_deleted", False)
            .execute()
        )
        
        if not response.data:
            raise ValueError("Establishment not found or access denied")
        
        return True

    def _check_event():
        # Если указано событие, проверяем что оно существует и принадлежит заведению
        if payload.event_id:
            response = (
                client.table("events")
                .select("id, establishment_id")
                .eq("id", payload.event_id)
                .eq("establishment_id", payload.establishment_id)
                .eq("is_deleted", False)
                .execute()
            )
            
            if not response.data:
                raise ValueError("Event not found or does not belong to this establishment")
        
        return True

    def _create():
        payment_link = generate_payment_link()
        
        # Проверяем уникальность ссылки (маловероятно, но на всякий случай)
        while True:
            check_response = (
                client.table("deposits")
                .select("id")
                .eq("payment_link", payment_link)
                .execute()
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
        
        response = client.table("deposits").insert(data).execute()
        
        if not response.data:
            raise ValueError("Failed to create deposit")
        
        return response.data[0]

    try:
        await run_in_threadpool(_check_establishment)
        await run_in_threadpool(_check_event)
        result = await run_in_threadpool(_create)
        return DepositResponse(**result)
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
    def _get():
        response = (
            client.table("deposits")
            .select("*, establishments!inner(owner_id)")
            .eq("id", deposit_id)
            .eq("is_deleted", False)
            .execute()
        )
        
        if not response.data:
            raise ValueError("Deposit not found")
        
        # Проверяем, что заведение принадлежит пользователю
        establishment = response.data[0].get("establishments")
        if not establishment or establishment.get("owner_id") != user_id:
            raise ValueError("Deposit not found or access denied")
        
        return response.data[0]

    try:
        result = await run_in_threadpool(_get)
        # Удаляем вложенный объект establishments из результата
        if "establishments" in result:
            del result["establishments"]
        return DepositResponse(**result)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
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
    def _get():
        response = (
            client.table("deposits")
            .select("*")
            .eq("payment_link", payment_link)
            .eq("is_deleted", False)
            .execute()
        )
        
        if not response.data:
            raise ValueError("Deposit not found")
        
        return response.data[0]

    try:
        result = await run_in_threadpool(_get)
        return DepositByLinkResponse(**result)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
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
    def _list():
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
        
        response = query.range(skip, skip + limit - 1).execute()
        
        results = response.data or []
        # Удаляем вложенные объекты establishments из результатов
        for item in results:
            if "establishments" in item:
                del item["establishments"]
        
        return results

    try:
        results = await run_in_threadpool(_list)
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
    def _check_access():
        # Проверяем доступ к депозиту
        response = (
            client.table("deposits")
            .select("*, establishments!inner(owner_id)")
            .eq("id", deposit_id)
            .eq("is_deleted", False)
            .execute()
        )
        
        if not response.data:
            raise ValueError("Deposit not found")
        
        establishment = response.data[0].get("establishments")
        if not establishment or establishment.get("owner_id") != user_id:
            raise ValueError("Deposit not found or access denied")
        
        return True

    def _update():
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
        
        response = (
            client.table("deposits")
            .update(data)
            .eq("id", deposit_id)
            .eq("is_deleted", False)
            .execute()
        )
        
        if not response.data:
            raise ValueError("Deposit not found, access denied, deleted, or update failed")
        
        return response.data[0]

    try:
        await run_in_threadpool(_check_access)
        result = await run_in_threadpool(_update)
        return DepositResponse(**result)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(f"Failed to update deposit: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update deposit: {exc}",
        ) from exc


async def delete_deposit(client: Client, deposit_id: str) -> dict[str, str]:
    """Удалить депозит (только для администраторов)"""
    def _delete():
        # Помечаем депозит как удаленный вместо физического удаления
        response = (
            client.table("deposits")
            .update({"is_deleted": True})
            .eq("id", deposit_id)
            .execute()
        )
        
        if not response.data:
            raise ValueError("Deposit not found")
        
        return {"message": "Deposit marked as deleted successfully"}

    try:
        return await run_in_threadpool(_delete)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(f"Failed to delete deposit: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete deposit: {exc}",
        ) from exc

