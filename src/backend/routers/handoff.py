import os
import urllib.parse
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from src.backend.database import get_db
from src.backend import models, schemas, crud
from src.backend.auth import get_current_user
from src.backend.config import RESEND_API_KEY, FRONTEND_URL

router = APIRouter(tags=["handoff"])


def _send_email(to: str, subject: str, html: str) -> None:
    if not RESEND_API_KEY:
        return
    try:
        import resend
        resend.api_key = RESEND_API_KEY
        resend.Emails.send({
            "from": "Calendo <noreply@calendo.app>",
            "to": [to],
            "subject": subject,
            "html": html,
        })
    except Exception:
        pass


def _platform_label(platform: str) -> str:
    return {"instagram": "Instagram", "x": "X", "tiktok": "TikTok", "linkedin": "LinkedIn", "facebook": "Facebook"}.get(platform, platform)


@router.post("/internal/notify-due")
def notify_due(request: Request, db: Session = Depends(get_db)):
    secret = request.headers.get("x-cron-secret", "")
    expected = os.getenv("INTERNAL_CRON_SECRET", "")
    if not expected or secret != expected:
        raise HTTPException(status_code=403, detail="Forbidden")

    now = datetime.utcnow()
    dialect = db.get_bind().dialect.name

    # 1. Ready-to-post: status='scheduled', scheduled_at <= now, notified_at IS NULL
    base_due = (
        db.query(models.Post)
        .filter(
            models.Post.status == models.StatusEnum.scheduled,
            models.Post.scheduled_at <= now,
            models.Post.notified_at.is_(None),
        )
    )
    if dialect == "postgresql":
        due_posts = base_due.with_for_update(skip_locked=True).all()
    else:
        due_posts = base_due.all()

    notified = []
    for post in due_posts:
        post.status = models.StatusEnum.ready
        post.notified_at = now
        db.add(post)
        user = db.query(models.User).filter(models.User.id == post.user_id).first()
        if user:
            handoff_url = f"{FRONTEND_URL}/dashboard"
            _send_email(
                user.email,
                f"Ready to post: {post.title}",
                (
                    f"<p>Your <strong>{_platform_label(post.platform.value)}</strong> post "
                    f"<em>{post.title}</em> is ready to go live.</p>"
                    f"<p><a href='{handoff_url}'>Open Calendo to post it now</a></p>"
                    f"<p style='color:#888'>Caption: {post.caption or '(no caption)'}</p>"
                ),
            )
        notified.append(post.id)

    # 2. Lead reminders: ~24h before, lead_notified_at IS NULL, user has enabled
    lead_start = now + timedelta(hours=23)
    lead_end = now + timedelta(hours=25)
    lead_posts = (
        db.query(models.Post)
        .join(models.User, models.Post.user_id == models.User.id)
        .filter(
            models.Post.status == models.StatusEnum.scheduled,
            models.Post.scheduled_at >= lead_start,
            models.Post.scheduled_at <= lead_end,
            models.Post.lead_notified_at.is_(None),
            models.User.lead_reminders_enabled.is_(True),
        )
        .all()
    )

    lead_notified = []
    for post in lead_posts:
        post.lead_notified_at = now
        db.add(post)
        user = db.query(models.User).filter(models.User.id == post.user_id).first()
        if user:
            _send_email(
                user.email,
                f"Heads up — posting in ~24h: {post.title}",
                (
                    f"<p>Your <strong>{_platform_label(post.platform.value)}</strong> post "
                    f"<em>{post.title}</em> goes live in about 24 hours.</p>"
                    f"<p><a href='{FRONTEND_URL}/dashboard'>Review it in Calendo</a></p>"
                ),
            )
        lead_notified.append(post.id)

    db.commit()
    return {"notified": notified, "lead_notified": lead_notified}


@router.get("/posts/{post_id}/handoff", response_model=schemas.HandoffResponse)
def get_handoff(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    post = crud.get_post_by_id(db, post_id)
    if not post or post.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Post not found")

    platform = post.platform.value
    caption = post.caption or ""
    caption_encoded = urllib.parse.quote(caption)

    if platform == "x":
        action = schemas.PlatformAction(
            type="intent",
            url=f"https://x.com/intent/post?text={caption_encoded}",
            note="Pre-fills caption. Add media manually after download.",
        )
    elif platform == "linkedin":
        action = schemas.PlatformAction(
            type="share",
            url=f"https://www.linkedin.com/sharing/share-offsite/?url={urllib.parse.quote(FRONTEND_URL)}&summary={caption_encoded}",
            note="LinkedIn pre-fill is limited to text and links.",
        )
    elif platform == "instagram":
        action = schemas.PlatformAction(
            type="open_app",
            url="instagram://app",
            note="Download media below, then paste caption in the app.",
        )
    elif platform == "facebook":
        action = schemas.PlatformAction(
            type="open_app",
            url="https://www.facebook.com/",
            note="No reliable pre-fill for Pages. Copy the caption, download media, then post on your Facebook Page.",
        )
    else:  # tiktok
        action = schemas.PlatformAction(
            type="open_app",
            url="https://www.tiktok.com/",
            note="Download media below, then paste caption in the app.",
        )

    media = [
        schemas.HandoffMediaItem(
            public_url=a.public_url,
            download_url=a.public_url,
            mime_type=a.mime_type,
        )
        for a in post.media_assets
    ]

    return schemas.HandoffResponse(
        post_id=post.id,
        caption=post.caption,
        platform=platform,
        media=media,
        platform_action=action,
        status=post.status.value,
    )


@router.post("/posts/{post_id}/mark-posted", response_model=schemas.PostResponse)
def mark_posted(
    post_id: int,
    body: schemas.MarkPostedBody,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    post = crud.get_post_by_id(db, post_id)
    if not post or post.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Post not found")

    post.status = models.StatusEnum.posted
    post.posted_at = datetime.utcnow()
    if body.posted_url:
        post.posted_url = body.posted_url
    db.commit()
    return crud.get_post_by_id(db, post_id)


@router.post("/posts/{post_id}/skip", response_model=schemas.PostResponse)
def skip_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    post = crud.get_post_by_id(db, post_id)
    if not post or post.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Post not found")

    post.status = models.StatusEnum.skipped
    db.commit()
    return crud.get_post_by_id(db, post_id)
