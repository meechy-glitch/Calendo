from datetime import date, datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from src.backend import models, schemas
from src.backend.auth import hash_password


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    db_user = models.User(
        email=user.email,
        hashed_password=hash_password(user.password),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_posts(
    db: Session, user_id: int, month: Optional[str] = None
) -> List[models.Post]:
    query = db.query(models.Post).filter(models.Post.user_id == user_id)
    if month:
        parts = month.split("-")
        year, m = int(parts[0]), int(parts[1])
        start = date(year, m, 1)
        end_month = m + 1 if m < 12 else 1
        end_year = year if m < 12 else year + 1
        end = date(end_year, end_month, 1)
        query = query.filter(
            models.Post.scheduled_date >= start,
            models.Post.scheduled_date < end,
        )
    return query.all()


def create_post(
    db: Session, post: schemas.PostCreate, user_id: int
) -> models.Post:
    post_data = post.model_dump()
    db_post = models.Post(**post_data, user_id=user_id)
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post


def get_post_by_id(db: Session, post_id: int) -> Optional[models.Post]:
    return db.query(models.Post).filter(models.Post.id == post_id).first()


def update_post(
    db: Session, post_id: int, post_update: schemas.PostUpdate, user_id: int
):
    db_post = get_post_by_id(db, post_id)
    if not db_post:
        return "not_found"
    if db_post.user_id != user_id:
        return "forbidden"
    for key, value in post_update.model_dump(exclude_unset=True).items():
        setattr(db_post, key, value)
    db.commit()
    db.refresh(db_post)
    return db_post


def delete_post(db: Session, post_id: int, user_id: int) -> str:
    db_post = get_post_by_id(db, post_id)
    if not db_post:
        return "not_found"
    if db_post.user_id != user_id:
        return "forbidden"
    db.delete(db_post)
    db.commit()
    return "deleted"


def create_media_asset(
    db: Session,
    user_id: int,
    storage_key: str,
    public_url: str,
    original_filename: str,
    mime_type: str,
    file_size_bytes: int,
) -> models.MediaAsset:
    asset = models.MediaAsset(
        user_id=user_id,
        storage_key=storage_key,
        public_url=public_url,
        original_filename=original_filename,
        mime_type=mime_type,
        file_size_bytes=file_size_bytes,
        status="uploaded",
        created_at=datetime.utcnow(),
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def get_media_asset(db: Session, asset_id: int, user_id: int) -> Optional[models.MediaAsset]:
    return (
        db.query(models.MediaAsset)
        .filter(models.MediaAsset.id == asset_id, models.MediaAsset.user_id == user_id)
        .first()
    )


def set_media_asset_ready(db: Session, asset_id: int, user_id: int) -> Optional[models.MediaAsset]:
    asset = get_media_asset(db, asset_id, user_id)
    if not asset:
        return None
    asset.status = "ready"
    db.commit()
    db.refresh(asset)
    return asset
