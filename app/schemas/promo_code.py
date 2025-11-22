from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, field_validator
from typing import Optional


class PromoCodeCreate(BaseModel):
    """Схема для создания промокода"""
    code: str
    promo_type: str  # 'fixed' или 'percentage'
    event_id: str
    discount_value: Decimal
    start_date: datetime
    end_date: datetime
    max_uses: Optional[int] = None
    is_active: bool = True

    @field_validator("promo_type")
    @classmethod
    def validate_promo_type(cls, v: str) -> str:
        if v not in ["fixed", "percentage"]:
            raise ValueError("Promo type must be 'fixed' or 'percentage'")
        return v

    @field_validator("discount_value")
    @classmethod
    def validate_discount_value(cls, v: Decimal, info) -> Decimal:
        promo_type = info.data.get("promo_type")
        if promo_type == "fixed":
            if v <= 0:
                raise ValueError("Fixed discount value must be greater than 0")
        elif promo_type == "percentage":
            if v <= 0 or v > 100:
                raise ValueError("Percentage discount value must be between 0 and 100")
        return v

    @field_validator("end_date")
    @classmethod
    def validate_dates(cls, v: datetime, info) -> datetime:
        start_date = info.data.get("start_date")
        if start_date and v <= start_date:
            raise ValueError("End date must be after start date")
        return v

    @field_validator("max_uses")
    @classmethod
    def validate_max_uses(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("Max uses must be greater than 0")
        return v


class PromoCodeUpdate(BaseModel):
    """Схема для обновления промокода"""
    code: Optional[str] = None
    discount_value: Optional[Decimal] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    max_uses: Optional[int] = None
    is_active: Optional[bool] = None

    @field_validator("discount_value")
    @classmethod
    def validate_discount_value(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v <= 0:
            raise ValueError("Discount value must be greater than 0")
        return v

    @field_validator("end_date")
    @classmethod
    def validate_dates(cls, v: Optional[datetime], info) -> Optional[datetime]:
        start_date = info.data.get("start_date")
        if v is not None and start_date and v <= start_date:
            raise ValueError("End date must be after start date")
        return v

    @field_validator("max_uses")
    @classmethod
    def validate_max_uses(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("Max uses must be greater than 0")
        return v


class PromoCodeValidate(BaseModel):
    """Схема для валидации промокода"""
    code: str
    event_id: str
    ticket_price: Decimal  # Цена билета для расчета скидки


class PromoCodeValidationResponse(BaseModel):
    """Ответ при валидации промокода"""
    valid: bool
    discount_amount: float
    final_price: float
    promo_code_id: Optional[str] = None
    message: Optional[str] = None


class PromoCodeResponse(BaseModel):
    """Схема для ответа с информацией о промокоде"""
    id: str
    code: str
    promo_type: str
    event_id: str
    discount_value: Decimal
    start_date: datetime
    end_date: datetime
    max_uses: Optional[int] = None
    current_uses: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    is_deleted: bool

    class Config:
        from_attributes = True
