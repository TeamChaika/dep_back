from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional


class TicketCreate(BaseModel):
    """Схема для создания билета"""
    event_id: str
    promo_code_id: Optional[str] = None
    guest_count: int
    first_name: str
    last_name: str
    phone: str
    email: Optional[EmailStr] = None
    table_number: Optional[str] = None
    comment: Optional[str] = None
    price: Decimal
    discount: Decimal = Decimal("0")

    @field_validator("guest_count")
    @classmethod
    def validate_guest_count(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Guest count must be greater than 0")
        return v

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Price cannot be negative")
        return v

    @field_validator("discount")
    @classmethod
    def validate_discount(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Discount cannot be negative")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # Базовая валидация телефона
        cleaned = "".join(filter(str.isdigit, v))
        if len(cleaned) < 10:
            raise ValueError("Invalid phone number")
        return v


class TicketUpdate(BaseModel):
    """Схема для обновления билета"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    table_number: Optional[str] = None
    comment: Optional[str] = None
    payment_status: Optional[str] = None
    guests_checked_in: Optional[int] = None
    sms_status: Optional[str] = None

    @field_validator("payment_status")
    @classmethod
    def validate_payment_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ["pending", "paid", "cancelled", "refunded"]:
            raise ValueError("Invalid payment status")
        return v

    @field_validator("sms_status")
    @classmethod
    def validate_sms_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ["pending", "sent", "failed"]:
            raise ValueError("Invalid SMS status")
        return v

    @field_validator("guests_checked_in")
    @classmethod
    def validate_guests_checked_in(cls, v: Optional[int], info) -> Optional[int]:
        if v is not None:
            if v < 0:
                raise ValueError("Guests checked in cannot be negative")
            # Проверка что не превышает guest_count будет в сервисе
        return v


class TicketCheckIn(BaseModel):
    """Схема для проверки билета (check-in)"""
    qr_code: str
    guests_count: int  # Сколько гостей заходит

    @field_validator("guests_count")
    @classmethod
    def validate_guests_count(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Guests count must be greater than 0")
        return v


class TicketResponse(BaseModel):
    """Схема для ответа с информацией о билете"""
    id: str
    event_id: str
    promo_code_id: Optional[str] = None
    guest_count: int
    first_name: str
    last_name: str
    phone: str
    email: Optional[str] = None
    payment_status: str
    table_number: Optional[str] = None
    comment: Optional[str] = None
    guests_checked_in: int
    sms_status: str
    price: Decimal
    discount: Decimal
    qr_code: str
    paid_at: Optional[datetime] = None
    checked_in_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

    class Config:
        from_attributes = True


class TicketByQRResponse(BaseModel):
    """Схема для ответа при получении билета по QR коду (публичный доступ)"""
    id: str
    event_id: str
    guest_count: int
    first_name: str
    last_name: str
    phone: str
    email: Optional[str] = None
    payment_status: str
    table_number: Optional[str] = None
    guests_checked_in: int
    qr_code: str
    checked_in_at: Optional[datetime] = None

    class Config:
        from_attributes = True
