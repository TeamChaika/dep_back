from __future__ import annotations

import re
from pydantic import BaseModel, field_validator
from typing import Optional, Any


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
    model_config = {"extra": "allow"}
    
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
        # Удаляем все пробелы и дефисы для проверки
        cleaned = re.sub(r"[\s-]", "", v)
        # Проверяем формат +7XXXXXXXXXX (11 цифр после +7)
        pattern = r"^\+7\d{10}$"
        if not re.match(pattern, cleaned):
            raise ValueError(
                "Телефон должен быть в формате +7###-###-##-## (например: +7999-123-45-67)"
            )
        # Возвращаем в формате с дефисами
        if "-" not in v:
            # Форматируем: +7XXX-XXX-XX-XX
            formatted = f"+7{cleaned[2:5]}-{cleaned[5:8]}-{cleaned[8:10]}-{cleaned[10:12]}"
            return formatted
        return v


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
    def validate_phone(cls, v: str) -> str:
        """Валидация телефона по маске +7###-###-##-##"""
        if v is None:
            return v
        # Удаляем все пробелы и дефисы для проверки
        cleaned = re.sub(r"[\s-]", "", v)
        # Проверяем формат +7XXXXXXXXXX (11 цифр после +7)
        pattern = r"^\+7\d{10}$"
        if not re.match(pattern, cleaned):
            raise ValueError(
                "Телефон должен быть в формате +7###-###-##-## (например: +7999-123-45-67)"
            )
        # Возвращаем в формате с дефисами
        if "-" not in v:
            # Форматируем: +7XXX-XXX-XX-XX
            formatted = f"+7{cleaned[2:5]}-{cleaned[5:8]}-{cleaned[8:10]}-{cleaned[10:12]}"
            return formatted
        return v


class EstablishmentResponse(BaseModel):
    """Схема для ответа с информацией о заведении"""
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

    class Config:
        from_attributes = True

