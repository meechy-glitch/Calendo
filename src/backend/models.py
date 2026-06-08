import enum
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, Column, Integer, String, Text, DateTime, Date, ForeignKey, Enum
from sqlalchemy.orm import relationship
from src.backend.database import Base


class PlatformEnum(str, enum.Enum):
    instagram = "instagram"
    x = "x"
    tiktok = "tiktok"
    linkedin = "linkedin"


class StatusEnum(str, enum.Enum):
    draft = "draft"
    scheduled = "scheduled"
    published = "published"


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
    status = Column(String(20), default="uploaded", nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="media_assets")
    posts = relationship("Post", back_populates="media_asset")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    posts = relationship("Post", back_populates="user")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user")
    brand_voice = relationship("BrandVoice", back_populates="user", uselist=False)
    media_assets = relationship("MediaAsset", back_populates="user")


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
    media_asset_id = Column(Integer, ForeignKey("media_asset.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="posts")
    media_asset = relationship("MediaAsset", back_populates="posts")


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
