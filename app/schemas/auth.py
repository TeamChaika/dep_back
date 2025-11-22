from __future__ import annotations

from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    phone: str
    first_name: str
    last_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    recovery_token: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    access_token: str
    new_password: str


class ChangeEmailRequest(BaseModel):
    access_token: str
    new_email: EmailStr


class LogoutRequest(BaseModel):
    access_token: str | None = None


class MessageResponse(BaseModel):
    message: str
    access_token: str | None = None

