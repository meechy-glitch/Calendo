import os
import secrets
import calendar
from datetime import datetime, timedelta, date
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.backend.database import get_db
from src.backend import schemas, crud, models
from src.backend.models import PlatformEnum, StatusEnum
from src.backend.auth import verify_password, create_access_token, hash_password
from src.backend.config import RESEND_API_KEY, FRONTEND_URL
from src.backend.auth import get_current_user

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/auth", tags=["auth"])


def _get_limit():
    if os.getenv("ENVIRONMENT") == "test":
        return "1000/minute"
    return "10/minute"


@router.post("/register", status_code=201, response_model=schemas.UserResponse)
@limiter.limit(_get_limit)
def register(
    request: Request,
    user: schemas.UserCreate,
    db: Session = Depends(get_db),
):
    if len(user.password) < 8:
        raise HTTPException(
            status_code=422, detail="Password must be at least 8 characters"
        )
    if crud.get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db, user)


@router.post("/login", response_model=schemas.Token)
@limiter.limit(_get_limit)
def login(
    request: Request,
    user: schemas.UserCreate,
    db: Session = Depends(get_db),
):
    db_user = crud.get_user_by_email(db, user.email)
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token, expires_in = create_access_token({"sub": str(db_user.id)})
    return {"access_token": token, "token_type": "bearer", "expires_in": expires_in}


@router.post("/forgot-password", status_code=200)
@limiter.limit(_get_limit)
def forgot_password(
    request: Request,
    body: schemas.ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    db_user = crud.get_user_by_email(db, body.email)
    # Always return success to avoid email enumeration
    if not db_user:
        return {"message": "If that email exists, a reset link has been sent"}

    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)
    reset_token = models.PasswordResetToken(
        token=token,
        user_id=db_user.id,
        expires_at=expires_at,
        used=False,
    )
    db.add(reset_token)
    db.commit()

    reset_url = f"{FRONTEND_URL}/reset-password?token={token}"

    if RESEND_API_KEY:
        try:
            import resend
            resend.api_key = RESEND_API_KEY
            resend.Emails.send({
                "from": "Calendo <noreply@calendo.app>",
                "to": [body.email],
                "subject": "Reset your Calendo password",
                "html": (
                    f"<p>Click the link below to reset your password. "
                    f"It expires in 1 hour.</p>"
                    f"<p><a href='{reset_url}'>{reset_url}</a></p>"
                    f"<p>If you didn't request this, ignore this email.</p>"
                ),
            })
        except Exception:
            pass

    return {"message": "If that email exists, a reset link has been sent"}


@router.post("/reset-password", status_code=200)
@limiter.limit(_get_limit)
def reset_password(
    request: Request,
    body: schemas.ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    reset_token = (
        db.query(models.PasswordResetToken)
        .filter(models.PasswordResetToken.token == body.token)
        .first()
    )
    if not reset_token:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    if reset_token.used:
        raise HTTPException(status_code=400, detail="Reset token has already been used")
    if reset_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Reset token has expired")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

    db_user = db.query(models.User).filter(models.User.id == reset_token.user_id).first()
    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    db_user.hashed_password = hash_password(body.new_password)
    reset_token.used = True
    db.commit()

    return {"message": "Password updated successfully"}


DEMO_EMAIL = "demo@calendo.app"
DEMO_PASSWORD = "demo1234"

_DEMO_POSTS = [
    {"title": "Product launch announcement", "platform": PlatformEnum.instagram, "status": StatusEnum.published, "day": 2, "scheduled_time": "10:00"},
    {"title": "Behind the scenes reel", "platform": PlatformEnum.tiktok, "status": StatusEnum.published, "day": 5, "scheduled_time": "14:30"},
    {"title": "Weekly tips thread", "platform": PlatformEnum.x, "status": StatusEnum.published, "day": 7, "scheduled_time": "09:00"},
    {"title": "Team spotlight", "platform": PlatformEnum.linkedin, "status": StatusEnum.published, "day": 9, "scheduled_time": "11:00"},
    {"title": "New feature drop", "platform": PlatformEnum.instagram, "status": StatusEnum.published, "day": 12, "scheduled_time": "16:00"},
    {"title": "Customer success story", "platform": PlatformEnum.linkedin, "status": StatusEnum.scheduled, "day": 14, "scheduled_time": "10:30"},
    {"title": "How we do it - BTS", "platform": PlatformEnum.tiktok, "status": StatusEnum.scheduled, "day": 16, "scheduled_time": "13:00"},
    {"title": "Industry insights", "platform": PlatformEnum.x, "status": StatusEnum.scheduled, "day": 18, "scheduled_time": "08:30"},
    {"title": "Weekend Q&A", "platform": PlatformEnum.instagram, "status": StatusEnum.scheduled, "day": 21, "scheduled_time": "12:00"},
    {"title": "Founder's note", "platform": PlatformEnum.linkedin, "status": StatusEnum.scheduled, "day": 23, "scheduled_time": "09:30"},
    {"title": "Product demo", "platform": PlatformEnum.tiktok, "status": StatusEnum.draft, "day": 25, "scheduled_time": "15:00"},
    {"title": "Trending audio drop", "platform": PlatformEnum.instagram, "status": StatusEnum.draft, "day": 26, "scheduled_time": None},
    {"title": "Partnership announcement", "platform": PlatformEnum.linkedin, "status": StatusEnum.draft, "day": 28, "scheduled_time": "11:30"},
    {"title": "Community highlights", "platform": PlatformEnum.x, "status": StatusEnum.draft, "day": 29, "scheduled_time": None},
    {"title": "Month recap reel", "platform": PlatformEnum.instagram, "status": StatusEnum.draft, "day": 30, "scheduled_time": "17:00"},
]

@router.post("/demo", response_model=schemas.Token)
def demo(db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, DEMO_EMAIL)
    if not db_user:
        demo_schema = schemas.UserCreate(email=DEMO_EMAIL, password=DEMO_PASSWORD)
        db_user = crud.create_user(db, demo_schema)
    else:
        db.query(models.Post).filter(models.Post.user_id == db_user.id).delete()
        db.commit()

    today = date.today()
    year = today.year
    month = today.month
    days_in_month = calendar.monthrange(year, month)[1]

    for post_data in _DEMO_POSTS:
        actual_day = min(post_data["day"], days_in_month)
        db_post = models.Post(
            user_id=db_user.id,
            title=post_data["title"],
            caption=None,
            platform=post_data["platform"],
            scheduled_date=date(year, month, actual_day),
            status=post_data["status"],
            scheduled_time=post_data["scheduled_time"],
            notes=None,
        )
        db.add(db_post)

    db.commit()

    token, expires_in = create_access_token({"sub": str(db_user.id)})
    return {"access_token": token, "token_type": "bearer", "expires_in": expires_in}


@router.get("/me", response_model=schemas.UserMeResponse)
def get_me(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return current_user


@router.patch("/me", response_model=schemas.UserMeResponse)
def update_me(
    body: schemas.UserMeUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if body.lead_reminders_enabled is not None:
        current_user.lead_reminders_enabled = body.lead_reminders_enabled
    db.commit()
    db.refresh(current_user)
    return current_user
