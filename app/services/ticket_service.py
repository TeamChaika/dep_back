from __future__ import annotations

import logging
import uuid
from datetime import datetime
from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from supabase import Client

from app.schemas.ticket import (
    TicketCreate,
    TicketUpdate,
    TicketResponse,
    TicketByQRResponse,
    TicketCheckIn,
)

logger = logging.getLogger(__name__)


def generate_qr_code() -> str:
    """Генерирует уникальный QR код для билета"""
    return f"TICKET-{uuid.uuid4().hex.upper()}"


async def create_ticket(
    client: Client, payload: TicketCreate, user_id: str
) -> TicketResponse:
    """Создать новый билет"""
    def _check_event():
        # Получаем событие
        event_response = (
            client.table("events")
            .select("id, establishment_id, ticket_types")
            .eq("id", payload.event_id)
            .eq("is_deleted", False)
            .execute()
        )
        
        if not event_response.data:
            raise ValueError("Event not found or access denied")
        
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
        
        return event

    def _check_promo_code():
        # Если указан промокод, проверяем его
        if payload.promo_code_id:
            response = (
                client.table("promo_codes")
                .select("id, current_uses, max_uses")
                .eq("id", payload.promo_code_id)
                .eq("is_deleted", False)
                .execute()
            )
            
            if not response.data:
                raise ValueError("Promo code not found")
            
            promo_code = response.data[0]
            if promo_code.get("max_uses") is not None:
                if promo_code.get("current_uses", 0) >= promo_code.get("max_uses"):
                    raise ValueError("Promo code limit exceeded")
        
        return True

    def _create():
        qr_code = generate_qr_code()
        
        # Проверяем уникальность QR кода
        while True:
            check_response = (
                client.table("tickets")
                .select("id")
                .eq("qr_code", qr_code)
                .execute()
            )
            if not check_response.data:
                break
            qr_code = generate_qr_code()
        
        data = {
            "event_id": payload.event_id,
            "promo_code_id": payload.promo_code_id,
            "guest_count": payload.guest_count,
            "first_name": payload.first_name,
            "last_name": payload.last_name,
            "phone": payload.phone,
            "email": payload.email,
            "table_number": payload.table_number,
            "comment": payload.comment,
            "payment_status": "pending",
            "guests_checked_in": 0,
            "sms_status": "pending",
            "price": float(payload.price),
            "discount": float(payload.discount),
            "qr_code": qr_code,
            "is_deleted": False,
        }
        
        response = client.table("tickets").insert(data).execute()
        
        if not response.data:
            raise ValueError("Failed to create ticket")
        
        # Увеличиваем счетчик использований промокода
        if payload.promo_code_id:
            promo_response = (
                client.table("promo_codes")
                .select("current_uses")
                .eq("id", payload.promo_code_id)
                .single()
                .execute()
            )
            if promo_response.data:
                current_uses = promo_response.data.get("current_uses", 0)
                client.table("promo_codes").update({
                    "current_uses": current_uses + 1
                }).eq("id", payload.promo_code_id).execute()
        
        return response.data[0]

    try:
        await run_in_threadpool(_check_event)
        await run_in_threadpool(_check_promo_code)
        result = await run_in_threadpool(_create)
        return TicketResponse(**result)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(f"Failed to create ticket: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create ticket: {exc}",
        ) from exc


async def get_ticket(
    client: Client, ticket_id: str, user_id: str
) -> TicketResponse:
    """Получить билет по ID"""
    def _get():
        # Получаем билет
        response = (
            client.table("tickets")
            .select("*")
            .eq("id", ticket_id)
            .eq("is_deleted", False)
            .execute()
        )
        
        if not response.data:
            raise ValueError("Ticket not found")
        
        ticket = response.data[0]
        event_id = ticket.get("event_id")
        
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
            raise ValueError("Ticket not found or access denied")
        
        return ticket

    try:
        result = await run_in_threadpool(_get)
        return TicketResponse(**result)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(f"Failed to get ticket: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get ticket: {exc}",
        ) from exc


async def get_ticket_by_qr(
    client: Client, qr_code: str
) -> TicketByQRResponse:
    """Получить билет по QR коду (публичный доступ)"""
    def _get():
        response = (
            client.table("tickets")
            .select("*")
            .eq("qr_code", qr_code)
            .eq("is_deleted", False)
            .execute()
        )
        
        if not response.data:
            raise ValueError("Ticket not found")
        
        return response.data[0]

    try:
        result = await run_in_threadpool(_get)
        return TicketByQRResponse(**result)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(f"Failed to get ticket by QR: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get ticket: {exc}",
        ) from exc


async def check_in_ticket(
    client: Client, qr_code: str, payload: TicketCheckIn
) -> TicketResponse:
    """Проверить билет (check-in)"""
    def _check_in():
        # Получаем билет
        response = (
            client.table("tickets")
            .select("*")
            .eq("qr_code", qr_code)
            .eq("is_deleted", False)
            .execute()
        )
        
        if not response.data:
            raise ValueError("Ticket not found")
        
        ticket = response.data[0]
        current_checked_in = ticket.get("guests_checked_in", 0)
        guest_count = ticket.get("guest_count", 0)
        
        # Проверяем, что не превышаем лимит
        if current_checked_in + payload.guests_count > guest_count:
            raise ValueError(
                f"Cannot check in {payload.guests_count} guests. "
                f"Only {guest_count - current_checked_in} guests remaining"
            )
        
        # Обновляем количество проверенных гостей
        new_checked_in = current_checked_in + payload.guests_count
        update_data = {
            "guests_checked_in": new_checked_in,
            "checked_in_at": datetime.now().isoformat(),
        }
        
        update_response = (
            client.table("tickets")
            .update(update_data)
            .eq("qr_code", qr_code)
            .execute()
        )
        
        if not update_response.data:
            raise ValueError("Failed to check in ticket")
        
        return update_response.data[0]

    try:
        result = await run_in_threadpool(_check_in)
        return TicketResponse(**result)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(f"Failed to check in ticket: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check in ticket: {exc}",
        ) from exc


async def list_tickets(
    client: Client, event_id: str | None, user_id: str, skip: int = 0, limit: int = 100
) -> list[TicketResponse]:
    """Получить список билетов"""
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
        
        # Теперь получаем билеты для этих событий
        query = (
            client.table("tickets")
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
        return [TicketResponse(**item) for item in results]
    except Exception as exc:
        logger.error(f"Failed to list tickets: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tickets: {exc}",
        ) from exc


async def update_ticket(
    client: Client, ticket_id: str, payload: TicketUpdate, user_id: str
) -> TicketResponse:
    """Обновить билет"""
    def _check_access():
        # Получаем билет
        ticket_response = (
            client.table("tickets")
            .select("event_id")
            .eq("id", ticket_id)
            .eq("is_deleted", False)
            .execute()
        )
        
        if not ticket_response.data:
            raise ValueError("Ticket not found")
        
        event_id = ticket_response.data[0].get("event_id")
        
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
            raise ValueError("Ticket not found or access denied")
        
        return True

    def _update():
        data = {}
        
        if payload.first_name is not None:
            data["first_name"] = payload.first_name
        if payload.last_name is not None:
            data["last_name"] = payload.last_name
        if payload.phone is not None:
            data["phone"] = payload.phone
        if payload.email is not None:
            data["email"] = payload.email
        if payload.table_number is not None:
            data["table_number"] = payload.table_number
        if payload.comment is not None:
            data["comment"] = payload.comment
        if payload.payment_status is not None:
            data["payment_status"] = payload.payment_status
            if payload.payment_status == "paid":
                data["paid_at"] = datetime.now().isoformat()
            elif payload.payment_status != "paid":
                data["paid_at"] = None
        if payload.guests_checked_in is not None:
            # Получаем текущий билет для проверки лимита
            current = (
                client.table("tickets")
                .select("guest_count")
                .eq("id", ticket_id)
                .single()
                .execute()
            )
            if current.data:
                if payload.guests_checked_in > current.data.get("guest_count", 0):
                    raise ValueError("Guests checked in cannot exceed guest count")
                data["guests_checked_in"] = payload.guests_checked_in
        if payload.sms_status is not None:
            data["sms_status"] = payload.sms_status
        
        if not data:
            raise ValueError("No fields to update")
        
        response = (
            client.table("tickets")
            .update(data)
            .eq("id", ticket_id)
            .eq("is_deleted", False)
            .execute()
        )
        
        if not response.data:
            raise ValueError("Ticket not found, access denied, deleted, or update failed")
        
        return response.data[0]

    try:
        await run_in_threadpool(_check_access)
        result = await run_in_threadpool(_update)
        return TicketResponse(**result)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(f"Failed to update ticket: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update ticket: {exc}",
        ) from exc


async def delete_ticket(client: Client, ticket_id: str) -> dict[str, str]:
    """Удалить билет (только для администраторов)"""
    def _delete():
        response = (
            client.table("tickets")
            .update({"is_deleted": True})
            .eq("id", ticket_id)
            .execute()
        )
        
        if not response.data:
            raise ValueError("Ticket not found")
        
        return {"message": "Ticket marked as deleted successfully"}

    try:
        return await run_in_threadpool(_delete)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(f"Failed to delete ticket: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete ticket: {exc}",
        ) from exc
