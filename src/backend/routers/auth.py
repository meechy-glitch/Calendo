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
    ("Product launch announcement", PlatformEnum.instagram, StatusEnum.published, 2, "10:00"),
    ("Behind the scenes reel", PlatformEnum.tiktok, StatusEnum.published, 5, "14:30"),
    ("Weekly tips thread", PlatformEnum.x, StatusEnum.published, 7, "09:00"),
    ("Team spotlight", PlatformEnum.linkedin, StatusEnum.published, 9, "11:00"),
    ("New feature drop", PlatformEnum.instagram, StatusEnum.published, 12, "16:00"),
    ("Customer success story", PlatformEnum.linkedin, StatusEnum.scheduled, 14, "10:30"),
    ("How we do it - BTS", PlatformEnum.tiktok, StatusEnum.scheduled, 16, "13:00"),
    ("Industry insights", PlatformEnum.x, StatusEnum.scheduled, 18, "08:30"),
    ("Weekend Q&A", PlatformEnum.instagram, StatusEnum.scheduled, 21, "12:00"),
    ("Founder's note", PlatformEnum.linkedin, StatusEnum.scheduled, 23, "09:30"),
    ("Product demo", PlatformEnum.tiktok, StatusEnum.draft, 25, "15:00"),
    ("Trending audio drop", PlatformEnum.instagram, StatusEnum.draft, 26, None),
    ("Partnership announcement", PlatformEnum.linkedin, StatusEnum.draft, 28, "11:30"),
    ("Community highlights", PlatformEnum.x, StatusEnum.draft, 29, None),
    ("Month recap reel", PlatformEnum.instagram, StatusEnum.draft, 30, "17:00"),
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

    for title, platform, status, day, sched_time in _DEMO_POSTS:
        actual_day = min(day, days_in_month)
        db_post = models.Post(
            user_id=db_user.id,
            title=title,
            caption=None,
            platform=platform,
            scheduled_date=date(year, month, actual_day),
            status=status,
            scheduled_time=sched_time,
            notes=None,
        )
        db.add(db_post)

    db.commit()

    token, expires_in = create_access_token({"sub": str(db_user.id)})
    return {"access_token": token, "token_type": "bearer", "expires_in": expires_in}
