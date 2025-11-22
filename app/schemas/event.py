from __future__ import annotations

from datetime import date, time, datetime
from pydantic import BaseModel, field_validator, model_validator
from typing import Optional


class TicketType(BaseModel):
    """Тип билета"""
    name: str
    price: float
    quantity: int
    available: int  # Доступное количество (может быть меньше quantity при продажах)


class EventCreate(BaseModel):
    """Схема для создания события"""
    establishment_id: str
    name: str
    description: Optional[str] = None
    event_date: date
    event_time: time
    poster_url: Optional[str] = None
    ticket_types: list[TicketType]
    start_sale_date: datetime
    end_sale_date: Optional[datetime] = None  # Если не указано, будет установлено как event_date + event_time

    @field_validator("ticket_types")
    @classmethod
    def validate_ticket_types(cls, v: list[TicketType]) -> list[TicketType]:
        if not v or len(v) == 0:
            raise ValueError("At least one ticket type is required")
        for ticket_type in v:
            if ticket_type.quantity <= 0:
                raise ValueError("Ticket quantity must be greater than 0")
            if ticket_type.price < 0:
                raise ValueError("Ticket price cannot be negative")
            if ticket_type.available > ticket_type.quantity:
                raise ValueError("Available tickets cannot exceed total quantity")
        return v

    @model_validator(mode="after")
    def set_default_end_sale_date(self) -> "EventCreate":
        """Устанавливает end_sale_date по умолчанию как дату и время мероприятия"""
        if self.end_sale_date is None:
            self.end_sale_date = datetime.combine(self.event_date, self.event_time)
        return self


class EventUpdate(BaseModel):
    """Схема для обновления события"""
    name: Optional[str] = None
    description: Optional[str] = None
    event_date: Optional[date] = None
    event_time: Optional[time] = None
    poster_url: Optional[str] = None
    ticket_types: Optional[list[TicketType]] = None
    start_sale_date: Optional[datetime] = None
    end_sale_date: Optional[datetime] = None

    @field_validator("ticket_types")
    @classmethod
    def validate_ticket_types(cls, v: Optional[list[TicketType]]) -> Optional[list[TicketType]]:
        if v is not None:
            if len(v) == 0:
                raise ValueError("At least one ticket type is required")
            for ticket_type in v:
                if ticket_type.quantity <= 0:
                    raise ValueError("Ticket quantity must be greater than 0")
                if ticket_type.price < 0:
                    raise ValueError("Ticket price cannot be negative")
                if ticket_type.available > ticket_type.quantity:
                    raise ValueError("Available tickets cannot exceed total quantity")
        return v


class EstablishmentInfo(BaseModel):
    """Информация о заведении для публичного доступа"""
    id: str
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None


class EventResponse(BaseModel):
    """Схема для ответа с информацией о событии"""
    id: str
    establishment_id: str
    name: str
    description: Optional[str] = None
    event_date: date
    event_time: time
    poster_url: Optional[str] = None
    ticket_types: list[TicketType]
    start_sale_date: datetime
    end_sale_date: datetime
    created_at: datetime
    updated_at: datetime
    is_deleted: bool
    establishments: Optional[EstablishmentInfo] = None  # Для публичного доступа

    class Config:
        from_attributes = True

