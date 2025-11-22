from __future__ import annotations

from datetime import date, time, datetime
from decimal import Decimal
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional


class DepositCreate(BaseModel):
    """Схема для создания депозита"""
    establishment_id: str
    event_id: Optional[str] = None
    guest_name: str
    guest_phone: str
    guest_email: Optional[EmailStr] = None
    amount: Decimal
    visit_date: date
    visit_time: time

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v

    @field_validator("guest_phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # Базовая валидация телефона
        cleaned = "".join(filter(str.isdigit, v))
        if len(cleaned) < 10:
            raise ValueError("Invalid phone number")
        return v


class DepositUpdate(BaseModel):
    """Схема для обновления депозита"""
    guest_name: Optional[str] = None
    guest_phone: Optional[str] = None
    guest_email: Optional[EmailStr] = None
    amount: Optional[Decimal] = None
    visit_date: Optional[date] = None
    visit_time: Optional[time] = None
    payment_status: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v

    @field_validator("payment_status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ["pending", "paid", "cancelled", "refunded"]:
            raise ValueError("Invalid payment status")
        return v


class DepositResponse(BaseModel):
    """Схема для ответа с информацией о депозите"""
    id: str
    establishment_id: str
    event_id: Optional[str] = None
    guest_name: str
    guest_phone: str
    guest_email: Optional[str] = None
    amount: Decimal
    visit_date: date
    visit_time: time
    payment_link: str
    payment_status: str
    paid_at: Optional[datetime] = None
    created_by: str
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

    class Config:
        from_attributes = True


class DepositByLinkResponse(BaseModel):
    """Схема для ответа при получении депозита по ссылке (публичный доступ)"""
    id: str
    establishment_id: str
    event_id: Optional[str] = None
    guest_name: str
    guest_phone: str
    guest_email: Optional[str] = None
    amount: Decimal
    visit_date: date
    visit_time: time
    payment_status: str
    paid_at: Optional[datetime] = None

    class Config:
        from_attributes = True

