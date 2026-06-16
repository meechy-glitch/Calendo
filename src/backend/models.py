import enum
from datetime import datetime
from sqlalchemy import (
    BigInteger, Boolean, Column, Float, Integer, String, Text,
    DateTime, Date, ForeignKey, Enum, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from src.backend.database import Base


class PlatformEnum(str, enum.Enum):
    instagram = "instagram"
    x = "x"
    tiktok = "tiktok"
    linkedin = "linkedin"
    facebook = "facebook"


class StatusEnum(str, enum.Enum):
    draft = "draft"
    scheduled = "scheduled"
    published = "published"
    ready = "ready"
    posted = "posted"
    skipped = "skipped"


class MediaAsset(Base):
    __tablename__ = "media_asset"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    storage_key = Column(Text, nullable=False)
    provider = Column(String(20), default="r2", nullable=False)
    public_url = Column(Text, nullable=True)
    original_filename = Column(String(255), nullable=True)
    mime_type = Column(String(100), nullable=True)
    file_size_bytes = Column(BigInteger, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    thumbnail_key = Column(Text, nullable=True)
    status = Column(String(20), default="uploaded", nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="media_assets")


class PostMedia(Base):
    __tablename__ = "post_media"

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    media_id = Column(Integer, ForeignKey("media_asset.id"), nullable=False)
    position = Column(Integer, default=0, nullable=False)

    __table_args__ = (UniqueConstraint("post_id", "position", name="uq_post_media_position"),)

    post = relationship("Post", back_populates="post_media_items")
    media = relationship("MediaAsset")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    lead_reminders_enabled = Column(Boolean, default=False, nullable=False, server_default="false")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    posts = relationship("Post", back_populates="user")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user")
    brand_voice = relationship("BrandVoice", back_populates="user", uselist=False)
    media_assets = relationship("MediaAsset", back_populates="user")
    memories = relationship("Memory", back_populates="user", cascade="all, delete-orphan")


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(100), nullable=False)
    caption = Column(String(2200), nullable=True)
    platform = Column(Enum(PlatformEnum, native_enum=False), nullable=False)
    scheduled_date = Column(Date, nullable=False)
    status = Column(Enum(StatusEnum, native_enum=False), default=StatusEnum.draft, nullable=False)
    scheduled_time = Column(String(5), nullable=True)
    notes = Column(String(500), nullable=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    notified_at = Column(DateTime(timezone=True), nullable=True)
    lead_notified_at = Column(DateTime(timezone=True), nullable=True)
    posted_at = Column(DateTime(timezone=True), nullable=True)
    posted_url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="posts")
    post_media_items = relationship(
        "PostMedia",
        back_populates="post",
        order_by="PostMedia.position",
        cascade="all, delete-orphan",
    )

    @property
    def media_assets(self):
        return [item.media for item in self.post_media_items]


class BrandVoice(Base):
    __tablename__ = "brand_voice"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    tone = Column(String(200), nullable=True)
    dos = Column(String(1000), nullable=True)
    donts = Column(String(1000), nullable=True)
    sample_posts = Column(String(2000), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="brand_voice")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(64), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="password_reset_tokens")


class Memory(Base):
    __tablename__ = "memory"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    type = Column(String(20), nullable=False)
    source = Column(String(20), nullable=False, default="assistant", server_default="assistant")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="memories")
