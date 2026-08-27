from datetime import date, datetime
from typing import Any, Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator
from src.backend.models import PlatformEnum, StatusEnum


NAME_MAX_LENGTH = 100


def _clean_name(value: object) -> str:
    """Strip surrounding whitespace and reject blank / too-short / too-long names.

    Raised as ValueError so pydantic reports it as a 422 with our own wording.
    """
    if not isinstance(value, str):
        raise ValueError("Name must be text")
    name = value.strip()
    if not name:
        raise ValueError("Name is required")
    if len(name) < 2:
        raise ValueError("Name must be at least 2 characters")
    if len(name) > NAME_MAX_LENGTH:
        raise ValueError(f"Name must be {NAME_MAX_LENGTH} characters or less")
    return name


class UserCreate(BaseModel):
    """Login credentials — also the shape used to seed the demo account."""

    email: EmailStr
    password: str


class UserRegister(BaseModel):
    """Registration payload. Name is required here but nullable in the DB,
    because accounts created before this feature have none."""

    email: EmailStr
    password: str = Field(min_length=8)
    name: str

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: object) -> str:
        return _clean_name(value)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str | None = None
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
    name: str | None = None
    lead_reminders_enabled: bool
    created_at: datetime


class UserMeUpdate(BaseModel):
    """Self-service profile update. Email is intentionally not editable."""

    name: str | None = None
    lead_reminders_enabled: bool | None = None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: object) -> str | None:
        # Omitting the field leaves the name untouched; sending null/blank is a
        # clear attempt to clear it, which we reject rather than silently allow.
        if value is None:
            raise ValueError("Name is required")
        return _clean_name(value)


class MemoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str
    type: str
    source: str
    created_at: datetime
