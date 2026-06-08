from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from src.backend import models, schemas
from src.backend.auth import hash_password


def _compute_scheduled_at(scheduled_date: date, scheduled_time: Optional[str], tz_name: str = "UTC") -> datetime:
    t = time.fromisoformat(scheduled_time) if scheduled_time else time(9, 0)
    naive_dt = datetime.combine(scheduled_date, t)
    try:
        zone = ZoneInfo(tz_name if tz_name else "UTC")
        aware_dt = naive_dt.replace(tzinfo=zone)
        return aware_dt.astimezone(timezone.utc).replace(tzinfo=None)
    except (ZoneInfoNotFoundError, Exception):
        return naive_dt


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


def _post_query(db: Session):
    return db.query(models.Post).options(
        joinedload(models.Post.post_media_items).joinedload(models.PostMedia.media)
    )


def get_posts(
    db: Session, user_id: int, month: Optional[str] = None, status: Optional[str] = None
) -> List[models.Post]:
    query = _post_query(db).filter(models.Post.user_id == user_id)
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
    if status:
        query = query.filter(models.Post.status == status)
    return query.all()


def create_post(
    db: Session, post: schemas.PostCreate, user_id: int
) -> models.Post:
    post_data = post.model_dump(exclude={"media_ids", "timezone"})
    post_data["scheduled_at"] = _compute_scheduled_at(
        post.scheduled_date, post.scheduled_time, post.timezone or "UTC"
    )
    db_post = models.Post(**post_data, user_id=user_id)
    db.add(db_post)
    db.flush()  # get id before inserting post_media

    if post.media_ids:
        for position, media_id in enumerate(post.media_ids):
            db.add(models.PostMedia(post_id=db_post.id, media_id=media_id, position=position))

    db.commit()
    db.refresh(db_post)
    # Re-fetch with eager loads
    return _post_query(db).filter(models.Post.id == db_post.id).one()


def get_post_by_id(db: Session, post_id: int) -> Optional[models.Post]:
    return _post_query(db).filter(models.Post.id == post_id).first()


def update_post(
    db: Session, post_id: int, post_update: schemas.PostUpdate, user_id: int
):
    db_post = get_post_by_id(db, post_id)
    if not db_post:
        return "not_found"
    if db_post.user_id != user_id:
        return "forbidden"

    update_data = post_update.model_dump(exclude_unset=True, exclude={"media_ids", "timezone"})
    for key, value in update_data.items():
        setattr(db_post, key, value)

    # Recompute scheduled_at if date or time changed
    new_date = post_update.scheduled_date or db_post.scheduled_date
    new_time = update_data.get("scheduled_time", db_post.scheduled_time)
    tz = post_update.timezone or "UTC"
    if post_update.scheduled_date is not None or "scheduled_time" in update_data:
        db_post.scheduled_at = _compute_scheduled_at(new_date, new_time, tz)

    if post_update.media_ids is not None:
        # Replace all media associations
        db.query(models.PostMedia).filter(models.PostMedia.post_id == post_id).delete()
        for position, media_id in enumerate(post_update.media_ids):
            db.add(models.PostMedia(post_id=post_id, media_id=media_id, position=position))

    db.commit()
    return _post_query(db).filter(models.Post.id == post_id).one()


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
