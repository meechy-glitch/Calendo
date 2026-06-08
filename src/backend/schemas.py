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


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class PresignRequest(BaseModel):
    filename: str
    content_type: str
    size_bytes: int


class PresignResponse(BaseModel):
    upload_url: str
    media_asset_id: int
    storage_key: str
    public_url: str
    expires_in: int


class ConfirmRequest(BaseModel):
    media_asset_id: int


class MediaAssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    storage_key: str
    public_url: Optional[str] = None
    original_filename: Optional[str] = None
    mime_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    status: str
    created_at: datetime


class PostCreate(BaseModel):
    title: str
    caption: Optional[str] = None
    platform: PlatformEnum
    scheduled_date: date
    status: StatusEnum = StatusEnum.draft
    scheduled_time: Optional[str] = None
    notes: Optional[str] = None
    media_asset_id: Optional[int] = None


class PostUpdate(BaseModel):
    title: Optional[str] = None
    caption: Optional[str] = None
    platform: Optional[PlatformEnum] = None
    scheduled_date: Optional[date] = None
    status: Optional[StatusEnum] = None
    scheduled_time: Optional[str] = None
    notes: Optional[str] = None
    media_asset_id: Optional[int] = None


class BrandVoiceUpsert(BaseModel):
    tone: Optional[str] = None
    dos: Optional[str] = None
    donts: Optional[str] = None
    sample_posts: Optional[str] = None


class BrandVoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tone: Optional[str] = None
    dos: Optional[str] = None
    donts: Optional[str] = None
    sample_posts: Optional[str] = None
    updated_at: Optional[datetime] = None


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
    media_asset_id: Optional[int] = None
    media_asset: Optional[MediaAssetResponse] = None
    created_at: datetime
    updated_at: datetime
