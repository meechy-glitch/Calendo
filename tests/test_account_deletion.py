"""Tests for DELETE /auth/me — permanent self-service account deletion."""
import os
os.environ.setdefault("GROQ_API_KEY", "test-key")

from datetime import datetime, timedelta

from src.backend import models
from src.backend.routers.auth import DEMO_EMAIL
from tests.conftest import TestingSessionLocal


def _seed_dependent_rows(db, user_id: int) -> None:
    """Give a user one row in every table that points at users.id."""
    post = models.Post(
        user_id=user_id,
        title="Scheduled post",
        caption="hello",
        platform=models.PlatformEnum.instagram,
        scheduled_date=datetime.utcnow().date(),
        status=models.StatusEnum.draft,
    )
    asset = models.MediaAsset(
        user_id=user_id,
        storage_key=f"users/{user_id}/media/pic.jpg",
        public_url="https://cdn.example.com/pic.jpg",
        mime_type="image/jpeg",
        status="ready",
    )
    db.add_all([post, asset])
    db.flush()

    db.add_all([
        models.PostMedia(post_id=post.id, media_id=asset.id, position=0),
        models.BrandVoice(user_id=user_id, tone="warm"),
        models.PasswordResetToken(
            token=f"reset-token-{user_id}",
            user_id=user_id,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        ),
        models.Memory(user_id=user_id, content="prefers short captions", type="preference"),
    ])
    db.commit()


def _row_counts(db, user_id: int) -> dict[str, int]:
    post_ids = [r[0] for r in db.query(models.Post.id).filter(models.Post.user_id == user_id)]
    return {
        "users": db.query(models.User).filter(models.User.id == user_id).count(),
        "posts": len(post_ids),
        "media_asset": db.query(models.MediaAsset)
            .filter(models.MediaAsset.user_id == user_id).count(),
        "post_media": (
            db.query(models.PostMedia)
            .filter(models.PostMedia.post_id.in_(post_ids)).count()
            if post_ids else 0
        ),
        "brand_voice": db.query(models.BrandVoice)
            .filter(models.BrandVoice.user_id == user_id).count(),
        "password_reset_tokens": db.query(models.PasswordResetToken)
            .filter(models.PasswordResetToken.user_id == user_id).count(),
        "memory": db.query(models.Memory)
            .filter(models.Memory.user_id == user_id).count(),
    }


def _register_and_login(client, email: str) -> tuple[int, dict[str, str]]:
    r = client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "name": "Other Person"},
    )
    assert r.status_code == 201
    user_id = r.json()["id"]
    r = client.post("/auth/login", json={"email": email, "password": "password123"})
    assert r.status_code == 200
    return user_id, {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_delete_me_removes_user_and_all_dependent_rows(client, auth_headers):
    db = TestingSessionLocal()
    user = db.query(models.User).filter(models.User.email == "test@example.com").first()
    user_id = user.id
    _seed_dependent_rows(db, user_id)
    before = _row_counts(db, user_id)
    db.close()
    assert all(count == 1 for count in before.values()), before

    r = client.delete("/auth/me", headers=auth_headers)
    assert r.status_code == 204

    db = TestingSessionLocal()
    after = _row_counts(db, user_id)
    db.close()
    assert after == {k: 0 for k in after}, after


def test_delete_me_leaves_other_users_data_untouched(client, auth_headers):
    db = TestingSessionLocal()
    victim = db.query(models.User).filter(models.User.email == "test@example.com").first()
    victim_id = victim.id
    _seed_dependent_rows(db, victim_id)
    db.close()

    bystander_id, _ = _register_and_login(client, "bystander@example.com")
    db = TestingSessionLocal()
    _seed_dependent_rows(db, bystander_id)
    db.close()

    r = client.delete("/auth/me", headers=auth_headers)
    assert r.status_code == 204

    db = TestingSessionLocal()
    assert _row_counts(db, victim_id) == {
        "users": 0, "posts": 0, "media_asset": 0, "post_media": 0,
        "brand_voice": 0, "password_reset_tokens": 0, "memory": 0,
    }
    bystander = _row_counts(db, bystander_id)
    db.close()
    assert all(count == 1 for count in bystander.values()), bystander


def test_delete_me_only_ever_targets_the_authenticated_user(client, auth_headers):
    """Another user's token deletes that user, never the caller named elsewhere."""
    db = TestingSessionLocal()
    target = db.query(models.User).filter(models.User.email == "test@example.com").first()
    target_id = target.id
    db.close()

    attacker_id, attacker_headers = _register_and_login(client, "attacker@example.com")

    # There is no id parameter to smuggle: naming a victim in the path is not
    # a route at all, and naming one in the body is ignored in favour of the JWT.
    assert client.delete(f"/auth/me/{target_id}", headers=attacker_headers).status_code == 404
    r = client.request(
        "DELETE", "/auth/me", headers=attacker_headers, json={"user_id": target_id}
    )
    assert r.status_code == 204

    db = TestingSessionLocal()
    assert db.query(models.User).filter(models.User.id == target_id).count() == 1
    assert db.query(models.User).filter(models.User.id == attacker_id).count() == 0
    db.close()

    # The victim's own credentials still work.
    r = client.post(
        "/auth/login", json={"email": "test@example.com", "password": "testpassword123"}
    )
    assert r.status_code == 200


def test_delete_me_requires_authentication(client, registered_user):
    assert client.delete("/auth/me").status_code == 403
    r = client.delete("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401

    db = TestingSessionLocal()
    assert db.query(models.User).filter(models.User.email == "test@example.com").count() == 1
    db.close()


def test_delete_me_rejects_the_shared_demo_account(client):
    r = client.post("/auth/demo")
    assert r.status_code == 200
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = client.delete("/auth/me", headers=headers)
    assert r.status_code == 403
    assert "demo account cannot be deleted" in r.json()["detail"]

    db = TestingSessionLocal()
    demo_user = db.query(models.User).filter(models.User.email == DEMO_EMAIL).first()
    assert demo_user is not None
    assert db.query(models.Post).filter(models.Post.user_id == demo_user.id).count() > 0
    db.close()


def test_token_is_useless_after_deletion(client, auth_headers):
    assert client.delete("/auth/me", headers=auth_headers).status_code == 204
    # The JWT is still unexpired, but get_current_user can no longer resolve it.
    assert client.get("/auth/me", headers=auth_headers).status_code == 401
    assert client.delete("/auth/me", headers=auth_headers).status_code == 401
