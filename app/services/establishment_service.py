from __future__ import annotations

import logging
from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from supabase import Client

from app.schemas.establishment import (
    EstablishmentCreate,
    EstablishmentUpdate,
    EstablishmentResponse,
)

logger = logging.getLogger(__name__)


async def create_establishment(
    client: Client, payload: EstablishmentCreate, user_id: str
) -> EstablishmentResponse:
    """Создать новое заведение"""
    def _create():
        # Преобразуем Pydantic модели в словари для Supabase
        working_hours_dict = payload.working_hours.model_dump() if payload.working_hours else {}
        # social_networks уже dict, не нужно вызывать model_dump()
        social_networks_dict = payload.social_networks if payload.social_networks else None
        
        data = {
            "name": payload.name,
            "phone": payload.phone,
            "address": payload.address,
            "working_hours": working_hours_dict,
            "social_networks": social_networks_dict,
            "description": payload.description,
            "owner_id": user_id,
            "is_deleted": False,
        }
        
        response = client.table("establishments").insert(data).execute()
        
        if not response.data:
            raise ValueError("Failed to create establishment")
        
        return response.data[0]

    try:
        result = await run_in_threadpool(_create)
        return EstablishmentResponse(**result)
    except Exception as exc:
        logger.error(f"Failed to create establishment: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create establishment: {exc}",
        ) from exc


async def get_establishment(
    client: Client, establishment_id: str, user_id: str
) -> EstablishmentResponse:
    """Получить заведение по ID (только если пользователь является владельцем и заведение не удалено)"""
    def _get():
        response = (
            client.table("establishments")
            .select("*")
            .eq("id", establishment_id)
            .eq("owner_id", user_id)
            .eq("is_deleted", False)
            .execute()
        )
        
        if not response.data:
            raise ValueError("Establishment not found or access denied")
        
        return response.data[0]

    try:
        result = await run_in_threadpool(_get)
        return EstablishmentResponse(**result)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(f"Failed to get establishment: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get establishment: {exc}",
        ) from exc


async def list_establishments(
    client: Client, user_id: str, skip: int = 0, limit: int = 100
) -> list[EstablishmentResponse]:
    """Получить список заведений пользователя (только не удаленные)"""
    def _list():
        response = (
            client.table("establishments")
            .select("*")
            .eq("owner_id", user_id)
            .eq("is_deleted", False)
            .order("created_at", desc=True)
            .range(skip, skip + limit - 1)
            .execute()
        )
        
        return response.data or []

    try:
        results = await run_in_threadpool(_list)
        return [EstablishmentResponse(**item) for item in results]
    except Exception as exc:
        logger.error(f"Failed to list establishments: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list establishments: {exc}",
        ) from exc


async def delete_establishment(client: Client, establishment_id: str) -> dict[str, str]:
    """Удалить заведение (только для администраторов)"""
    def _delete():
        # Помечаем заведение как удаленное вместо физического удаления
        response = (
            client.table("establishments")
            .update({"is_deleted": True})
            .eq("id", establishment_id)
            .execute()
        )
        
        if not response.data:
            raise ValueError("Establishment not found")
        
        return {"message": "Establishment marked as deleted successfully"}

    try:
        return await run_in_threadpool(_delete)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(f"Failed to delete establishment: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete establishment: {exc}",
        ) from exc


async def update_establishment(
    client: Client, establishment_id: str, payload: EstablishmentUpdate, user_id: str
) -> EstablishmentResponse:
    """Обновить заведение"""
    def _update():
        # Собираем только переданные поля
        data = {}
        
        if payload.name is not None:
            data["name"] = payload.name
        if payload.phone is not None:
            data["phone"] = payload.phone
        if payload.address is not None:
            data["address"] = payload.address
        if payload.working_hours is not None:
            data["working_hours"] = payload.working_hours.model_dump()
        if payload.social_networks is not None:
            # social_networks уже dict, не нужно вызывать model_dump()
            data["social_networks"] = payload.social_networks
        if payload.description is not None:
            data["description"] = payload.description
        
        if not data:
            raise ValueError("No fields to update")
        
        response = (
            client.table("establishments")
            .update(data)
            .eq("id", establishment_id)
            .eq("owner_id", user_id)
            .eq("is_deleted", False)
            .execute()
        )
        
        if not response.data:
            raise ValueError("Establishment not found, access denied, deleted, or update failed")
        
        return response.data[0]

    try:
        result = await run_in_threadpool(_update)
        return EstablishmentResponse(**result)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error(f"Failed to update establishment: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update establishment: {exc}",
        ) from exc



