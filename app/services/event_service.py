from __future__ import annotations

import logging
from datetime import date, time, datetime
from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from supabase import Client

from app.schemas.event import (
    EventCreate,
    EventUpdate,
    EventResponse,
    TicketType,
)

logger = logging.getLogger(__name__)


async def create_event(
    client: Client, payload: EventCreate, user_id: str
) -> EventResponse:
    """Создать новое событие"""
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

    def _create():
        # Преобразуем ticket_types в JSON
        ticket_types_json = [ticket.model_dump() for ticket in payload.ticket_types]
        
        # end_sale_date уже установлен валидатором, если не был указан
        end_sale_date = payload.end_sale_date
        
        data = {
            "establishment_id": payload.establishment_id,
            "name": payload.name,
            "description": payload.description,
            "event_date": str(payload.event_date),
            "event_time": str(payload.event_time),
            "poster_url": payload.poster_url,
            "ticket_types": ticket_types_json,
            "start_sale_date": payload.start_sale_date.isoformat(),
            "end_sale_date": end_sale_date.isoformat(),
            "is_deleted": False,
        }
        
        response = client.table("events").insert(data).execute()
        
        if not response.data:
            raise ValueError("Failed to create event")
        
        return response.data[0]

    try:
        # Проверяем доступ к заведению
        await run_in_threadpool(_check_establishment)
        # Создаем событие
        result = await run_in_threadpool(_create)
        return EventResponse(**result)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(f"Failed to create event: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create event: {exc}",
        ) from exc


async def get_event(
    client: Client, event_id: str, user_id: str
) -> EventResponse:
    """Получить событие по ID (только если пользователь является владельцем заведения)"""
    def _get():
        response = (
            client.table("events")
            .select("*, establishments!inner(owner_id)")
            .eq("id", event_id)
            .eq("is_deleted", False)
            .execute()
        )
        
        if not response.data:
            raise ValueError("Event not found")
        
        # Проверяем, что заведение принадлежит пользователю
        establishment = response.data[0].get("establishments")
        if not establishment or establishment.get("owner_id") != user_id:
            raise ValueError("Event not found or access denied")
        
        return response.data[0]

    try:
        result = await run_in_threadpool(_get)
        # Удаляем вложенный объект establishments из результата
        if "establishments" in result:
            del result["establishments"]
        return EventResponse(**result)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(f"Failed to get event: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get event: {exc}",
        ) from exc


async def get_event_public(
    client: Client, event_id: str
) -> EventResponse:
    """Получить событие по ID (публичный доступ)"""
    def _get():
        # Получаем событие
        event_response = (
            client.table("events")
            .select("*")
            .eq("id", event_id)
            .eq("is_deleted", False)
            .execute()
        )
        
        if not event_response.data:
            raise ValueError("Event not found")
        
        event = event_response.data[0]
        establishment_id = event.get("establishment_id")
        
        # Получаем информацию о заведении
        if establishment_id:
            establishment_response = (
                client.table("establishments")
                .select("id, name, address, phone")
                .eq("id", establishment_id)
                .eq("is_deleted", False)
                .execute()
            )
            
            if establishment_response.data:
                event["establishments"] = establishment_response.data[0]
        
        return event

    try:
        result = await run_in_threadpool(_get)
        return EventResponse(**result)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(f"Failed to get event: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get event: {exc}",
        ) from exc


async def list_events(
    client: Client, establishment_id: str | None, user_id: str, skip: int = 0, limit: int = 100
) -> list[EventResponse]:
    """Получить список событий (только для заведений пользователя)"""
    def _list():
        query = (
            client.table("events")
            .select("*, establishments!inner(owner_id)")
            .eq("establishments.owner_id", user_id)
            .eq("is_deleted", False)
            .order("event_date", desc=False)
            .order("event_time", desc=False)
        )
        
        if establishment_id:
            query = query.eq("establishment_id", establishment_id)
        
        response = query.range(skip, skip + limit - 1).execute()
        
        results = response.data or []
        # Удаляем вложенные объекты establishments из результатов
        for item in results:
            if "establishments" in item:
                del item["establishments"]
        
        return results

    try:
        results = await run_in_threadpool(_list)
        return [EventResponse(**item) for item in results]
    except Exception as exc:
        logger.error(f"Failed to list events: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list events: {exc}",
        ) from exc


async def update_event(
    client: Client, event_id: str, payload: EventUpdate, user_id: str
) -> EventResponse:
    """Обновить событие"""
    def _check_access():
        # Проверяем доступ к событию
        response = (
            client.table("events")
            .select("*, establishments!inner(owner_id)")
            .eq("id", event_id)
            .eq("is_deleted", False)
            .execute()
        )
        
        if not response.data:
            raise ValueError("Event not found")
        
        establishment = response.data[0].get("establishments")
        if not establishment or establishment.get("owner_id") != user_id:
            raise ValueError("Event not found or access denied")
        
        return True

    def _update():
        # Собираем только переданные поля
        data = {}
        
        if payload.name is not None:
            data["name"] = payload.name
        if payload.description is not None:
            data["description"] = payload.description
        if payload.event_date is not None:
            data["event_date"] = payload.event_date.isoformat()
        if payload.event_time is not None:
            data["event_time"] = payload.event_time.isoformat()
        if payload.poster_url is not None:
            data["poster_url"] = payload.poster_url
        if payload.ticket_types is not None:
            data["ticket_types"] = [ticket.model_dump() for ticket in payload.ticket_types]
        if payload.start_sale_date is not None:
            data["start_sale_date"] = payload.start_sale_date.isoformat()
        if payload.end_sale_date is not None:
            data["end_sale_date"] = payload.end_sale_date.isoformat()
        
        # Если обновляется event_date или event_time, и end_sale_date не указан,
        # нужно пересчитать end_sale_date
        if (payload.event_date is not None or payload.event_time is not None) and payload.end_sale_date is None:
            # Получаем текущие данные события
            current_response = (
                client.table("events")
                .select("event_date, event_time")
                .eq("id", event_id)
                .execute()
            )
            if current_response.data:
                current = current_response.data[0]
                event_date = payload.event_date or date.fromisoformat(current["event_date"])
                event_time = payload.event_time or time.fromisoformat(current["event_time"])
                data["end_sale_date"] = datetime.combine(event_date, event_time).isoformat()
        
        if not data:
            raise ValueError("No fields to update")
        
        response = (
            client.table("events")
            .update(data)
            .eq("id", event_id)
            .eq("is_deleted", False)
            .execute()
        )
        
        if not response.data:
            raise ValueError("Event not found, access denied, deleted, or update failed")
        
        return response.data[0]

    try:
        await run_in_threadpool(_check_access)
        result = await run_in_threadpool(_update)
        return EventResponse(**result)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(f"Failed to update event: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update event: {exc}",
        ) from exc


async def delete_event(client: Client, event_id: str) -> dict[str, str]:
    """Удалить событие (только для администраторов)"""
    def _delete():
        # Помечаем событие как удаленное вместо физического удаления
        response = (
            client.table("events")
            .update({"is_deleted": True})
            .eq("id", event_id)
            .execute()
        )
        
        if not response.data:
            raise ValueError("Event not found")
        
        return {"message": "Event marked as deleted successfully"}

    try:
        return await run_in_threadpool(_delete)
    except Exception as exc:
        logger.error(f"Failed to delete event: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete event: {exc}",
        ) from exc
