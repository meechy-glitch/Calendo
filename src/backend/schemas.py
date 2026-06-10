from datetime import date, datetime
from typing import Any, Optional, List
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
    width: Optional[int] = None
    height: Optional[int] = None
    duration_seconds: Optional[float] = None
    thumbnail_key: Optional[str] = None
    status: str
    created_at: datetime
    # Per-platform spec warnings for video assets; populated by the media router
    spec_warnings: Optional[dict[str, Any]] = None


class PostCreate(BaseModel):
    title: str
    caption: Optional[str] = None
    platform: PlatformEnum
    scheduled_date: date
    status: StatusEnum = StatusEnum.draft
    scheduled_time: Optional[str] = None
    notes: Optional[str] = None
    media_ids: Optional[List[int]] = None
    timezone: Optional[str] = "UTC"


class PostUpdate(BaseModel):
    title: Optional[str] = None
    caption: Optional[str] = None
    platform: Optional[PlatformEnum] = None
    scheduled_date: Optional[date] = None
    status: Optional[StatusEnum] = None
    scheduled_time: Optional[str] = None
    notes: Optional[str] = None
    media_ids: Optional[List[int]] = None
    timezone: Optional[str] = None


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
    scheduled_at: Optional[datetime] = None
    status: StatusEnum
    scheduled_time: Optional[str] = None
    notes: Optional[str] = None
    notified_at: Optional[datetime] = None
    lead_notified_at: Optional[datetime] = None
    posted_at: Optional[datetime] = None
    posted_url: Optional[str] = None
    media_assets: List[MediaAssetResponse] = []
    created_at: datetime
    updated_at: datetime


class MarkPostedBody(BaseModel):
    posted_url: Optional[str] = None


class HandoffMediaItem(BaseModel):
    public_url: Optional[str] = None
    download_url: Optional[str] = None
    mime_type: Optional[str] = None


class PlatformAction(BaseModel):
    type: str
    url: str
    note: Optional[str] = None


class HandoffResponse(BaseModel):
    post_id: int
    caption: Optional[str] = None
    platform: str
    media: List[HandoffMediaItem] = []
    platform_action: PlatformAction
    status: str


class UserMeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    lead_reminders_enabled: bool
    created_at: datetime


class UserMeUpdate(BaseModel):
    lead_reminders_enabled: Optional[bool] = None


class MemoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str
    type: str
    source: str
    created_at: datetime
