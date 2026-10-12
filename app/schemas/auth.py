from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    display_name: str
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'


class UserMe(BaseModel):
    id: uuid.UUID
    email: EmailStr
    display_name: str
    is_active: bool
