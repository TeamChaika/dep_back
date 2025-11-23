from __future__ import annotations

from typing import Optional, Any

from pydantic import BaseModel, field_validator, ConfigDict

from app.utils.validators import validate_phone_number


class WorkingHours(BaseModel):
    """Режим работы для одного дня"""
    open_time: str  # Формат "HH:MM"
    close_time: str  # Формат "HH:MM"
    is_closed: bool = False  # Если заведение закрыто в этот день


class WeeklySchedule(BaseModel):
    """Режим работы на неделю"""
    monday: Optional[WorkingHours] = None
    tuesday: Optional[WorkingHours] = None
    wednesday: Optional[WorkingHours] = None
    thursday: Optional[WorkingHours] = None
    friday: Optional[WorkingHours] = None
    saturday: Optional[WorkingHours] = None
    sunday: Optional[WorkingHours] = None


class SocialNetworks(BaseModel):
    """Социальные сети заведения - поддерживает произвольные ключи"""
    model_config = ConfigDict(extra="allow")
    
    instagram: Optional[str] = None
    facebook: Optional[str] = None
    vk: Optional[str] = None
    telegram: Optional[str] = None
    website: Optional[str] = None


class EstablishmentCreate(BaseModel):
    """Схема для создания заведения"""
    name: str
    phone: str
    address: str
    working_hours: WeeklySchedule
    social_networks: Optional[dict[str, Any]] = None  # Произвольные ключи для кастомных соц сетей
    description: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Валидация телефона по маске +7###-###-##-##"""
        result = validate_phone_number(v)
        if result is None:
            # This should technically not happen if the field is required str, 
            # but Pydantic validation flow might be complex.
            # If v was somehow None, Pydantic would likely catch it before validation if it's not Optional.
            # But let's be safe.
            raise ValueError("Phone number is required")
        return result


class EstablishmentUpdate(BaseModel):
    """Схема для обновления заведения"""
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    working_hours: Optional[WeeklySchedule] = None
    social_networks: Optional[dict[str, Any]] = None
    description: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        """Валидация телефона по маске +7###-###-##-##"""
        return validate_phone_number(v)


class EstablishmentResponse(BaseModel):
    """Схема для ответа с информацией о заведении"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    phone: str
    address: str
    working_hours: WeeklySchedule
    social_networks: Optional[dict[str, Any]] = None
    description: Optional[str] = None
    owner_id: str
    created_at: str
    updated_at: str
