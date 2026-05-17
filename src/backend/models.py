import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Enum
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


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    posts = relationship("Post", back_populates="user")


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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="posts")
