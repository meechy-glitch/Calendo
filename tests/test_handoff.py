import os
os.environ["INTERNAL_CRON_SECRET"] = "test-secret"

from datetime import datetime, timedelta
from tests.conftest import *  # noqa: F401,F403


POST_DATA = {
    "title": "Launch post",
    "caption": "Check it out!",
    "platform": "x",
    "scheduled_date": "2025-05-15",
    "status": "scheduled",
    "scheduled_time": "10:00",
}

CRON_HEADERS = {"x-cron-secret": "test-secret"}


# ── /internal/notify-due ───────────────────────────────────────────────────

def test_notify_due_forbidden_without_secret(client):
    r = client.post("/internal/notify-due")
    assert r.status_code == 403


def test_notify_due_forbidden_wrong_secret(client):
    r = client.post("/internal/notify-due", headers={"x-cron-secret": "wrong"})
    assert r.status_code == 403


def test_notify_due_no_posts(client):
    r = client.post("/internal/notify-due", headers=CRON_HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["notified"] == []
    assert data["lead_notified"] == []


def test_notify_due_moves_overdue_post_to_ready(client, auth_headers):
    # Create a post with scheduled_at in the past
    r = client.post("/posts", json=POST_DATA, headers=auth_headers)
    assert r.status_code == 201
    post_id = r.json()["id"]

    # Manually set scheduled_at to past via a direct update (simulate past due)
    from tests.conftest import TestingSessionLocal
    from src.backend import models
    db = TestingSessionLocal()
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    post.scheduled_at = datetime.utcnow() - timedelta(minutes=5)
    db.commit()
    db.close()

    r = client.post("/internal/notify-due", headers=CRON_HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert post_id in data["notified"]

    # Post should now be 'ready'
    r = client.get(f"/posts/{post_id}", headers=auth_headers)
    assert r.json()["status"] == "ready"
    assert r.json()["notified_at"] is not None


def test_notify_due_does_not_double_notify(client, auth_headers):
    r = client.post("/posts", json=POST_DATA, headers=auth_headers)
    post_id = r.json()["id"]

    from tests.conftest import TestingSessionLocal
    from src.backend import models
    db = TestingSessionLocal()
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    post.scheduled_at = datetime.utcnow() - timedelta(minutes=5)
    db.commit()
    db.close()

    client.post("/internal/notify-due", headers=CRON_HEADERS)
    r2 = client.post("/internal/notify-due", headers=CRON_HEADERS)
    assert r2.json()["notified"] == []


# ── GET /posts/{id}/handoff ────────────────────────────────────────────────

def test_handoff_x_returns_intent(client, auth_headers):
    r = client.post("/posts", json=POST_DATA, headers=auth_headers)
    post_id = r.json()["id"]
    r = client.get(f"/posts/{post_id}/handoff", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["platform"] == "x"
    assert "x.com/intent/post" in data["platform_action"]["url"]
    assert data["platform_action"]["type"] == "intent"


def test_handoff_instagram_returns_open_app(client, auth_headers):
    r = client.post("/posts", json={**POST_DATA, "platform": "instagram"}, headers=auth_headers)
    post_id = r.json()["id"]
    r = client.get(f"/posts/{post_id}/handoff", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["platform_action"]["type"] == "open_app"
    assert "instagram" in r.json()["platform_action"]["url"]


def test_handoff_linkedin_returns_share(client, auth_headers):
    r = client.post("/posts", json={**POST_DATA, "platform": "linkedin"}, headers=auth_headers)
    post_id = r.json()["id"]
    r = client.get(f"/posts/{post_id}/handoff", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["platform_action"]["type"] == "share"
    assert "linkedin.com" in r.json()["platform_action"]["url"]


def test_handoff_not_found(client, auth_headers):
    r = client.get("/posts/99999/handoff", headers=auth_headers)
    assert r.status_code == 404


def test_handoff_other_user_forbidden(client, auth_headers):
    r = client.post("/posts", json=POST_DATA, headers=auth_headers)
    post_id = r.json()["id"]

    # Register a second user
    client.post("/auth/register", json={"email": "other@example.com", "password": "pass1234"})
    login = client.post("/auth/login", json={"email": "other@example.com", "password": "pass1234"})
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    r = client.get(f"/posts/{post_id}/handoff", headers=other_headers)
    assert r.status_code == 404


# ── POST /posts/{id}/mark-posted ───────────────────────────────────────────

def test_mark_posted(client, auth_headers):
    r = client.post("/posts", json=POST_DATA, headers=auth_headers)
    post_id = r.json()["id"]
    r = client.post(f"/posts/{post_id}/mark-posted", json={}, headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "posted"
    assert data["posted_at"] is not None
    assert data["posted_url"] is None


def test_mark_posted_with_url(client, auth_headers):
    r = client.post("/posts", json=POST_DATA, headers=auth_headers)
    post_id = r.json()["id"]
    r = client.post(
        f"/posts/{post_id}/mark-posted",
        json={"posted_url": "https://x.com/user/status/123"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["posted_url"] == "https://x.com/user/status/123"


def test_mark_posted_not_found(client, auth_headers):
    r = client.post("/posts/99999/mark-posted", json={}, headers=auth_headers)
    assert r.status_code == 404


# ── POST /posts/{id}/skip ──────────────────────────────────────────────────

def test_skip_post(client, auth_headers):
    r = client.post("/posts", json=POST_DATA, headers=auth_headers)
    post_id = r.json()["id"]
    r = client.post(f"/posts/{post_id}/skip", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "skipped"


def test_skip_not_found(client, auth_headers):
    r = client.post("/posts/99999/skip", headers=auth_headers)
    assert r.status_code == 404


# ── GET /posts/ready-queue ─────────────────────────────────────────────────

def test_ready_queue_empty(client, auth_headers):
    r = client.get("/posts/ready-queue", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_ready_queue_returns_ready_posts(client, auth_headers):
    r = client.post("/posts", json=POST_DATA, headers=auth_headers)
    post_id = r.json()["id"]
    client.post(f"/posts/{post_id}/mark-posted", json={}, headers=auth_headers)

    r2 = client.post("/posts", json={**POST_DATA, "title": "Another"}, headers=auth_headers)
    post_id2 = r2.json()["id"]

    # Mark as ready directly
    from tests.conftest import TestingSessionLocal
    from src.backend import models
    db = TestingSessionLocal()
    post = db.query(models.Post).filter(models.Post.id == post_id2).first()
    post.status = models.StatusEnum.ready
    db.commit()
    db.close()

    r = client.get("/posts/ready-queue", headers=auth_headers)
    assert r.status_code == 200
    ids = [p["id"] for p in r.json()]
    assert post_id2 in ids
    assert post_id not in ids


# ── GET /auth/me & PATCH /auth/me ─────────────────────────────────────────

def test_get_me(client, auth_headers):
    r = client.get("/auth/me", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "test@example.com"
    assert data["lead_reminders_enabled"] is False


def test_patch_me_lead_reminders(client, auth_headers):
    r = client.patch("/auth/me", json={"lead_reminders_enabled": True}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["lead_reminders_enabled"] is True

    r2 = client.get("/auth/me", headers=auth_headers)
    assert r2.json()["lead_reminders_enabled"] is True


def test_scheduled_at_set_on_create(client, auth_headers):
    r = client.post("/posts", json=POST_DATA, headers=auth_headers)
    assert r.status_code == 201
    data = r.json()
    assert data["scheduled_at"] is not None
    # Should encode 2025-05-15T10:00:00 UTC
    assert "2025-05-15" in data["scheduled_at"]
