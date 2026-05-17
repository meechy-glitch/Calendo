from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict
from src.backend.models import PlatformEnum, StatusEnum


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class PostCreate(BaseModel):
    title: str
    caption: Optional[str] = None
    platform: PlatformEnum
    scheduled_date: date
    status: StatusEnum = StatusEnum.draft
    scheduled_time: Optional[str] = None
    notes: Optional[str] = None


class PostUpdate(BaseModel):
    title: Optional[str] = None
    caption: Optional[str] = None
    platform: Optional[PlatformEnum] = None
    scheduled_date: Optional[date] = None
    status: Optional[StatusEnum] = None
    scheduled_time: Optional[str] = None
    notes: Optional[str] = None


class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    caption: Optional[str] = None
    platform: PlatformEnum
    scheduled_date: date
    status: StatusEnum
    scheduled_time: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
