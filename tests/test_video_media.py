"""Tests for Phase 4 video upload, post_media junction, and spec validation."""
import os
os.environ.setdefault("GROQ_API_KEY", "test-key")

from unittest.mock import MagicMock, patch

import pytest

from src.backend import models
from src.backend.routers.media import _video_spec_warnings
from tests.conftest import TestingSessionLocal


# ── spec warnings ─────────────────────────────────────────────────────────────

class _FakeAsset:
    """Plain object that looks like MediaAsset for spec-warning unit tests."""
    def __init__(self, **kwargs):
        defaults = dict(
            id=1,
            user_id=1,
            storage_key="users/1/media/v.mp4",
            public_url="https://cdn.example.com/users/1/media/v.mp4",
            mime_type="video/mp4",
            file_size_bytes=10 * 1024 * 1024,
            width=1080,
            height=1920,
            duration_seconds=30.0,
            thumbnail_key=None,
            status="ready",
        )
        defaults.update(kwargs)
        for k, v in defaults.items():
            setattr(self, k, v)


def _make_video_asset(**kwargs):
    return _FakeAsset(**kwargs)


def test_spec_warnings_clean_vertical_mp4():
    asset = _make_video_asset()
    warnings = _video_spec_warnings(asset)
    assert warnings["x"] == []
    assert warnings["linkedin"] == []
    assert warnings["instagram"] == []
    assert warnings["tiktok"] == []


def test_spec_warnings_too_large_for_x():
    asset = _make_video_asset(file_size_bytes=60 * 1024 * 1024)
    warnings = _video_spec_warnings(asset)
    assert any("50 MB" in w for w in warnings["x"])
    assert warnings["linkedin"] == []


def test_spec_warnings_duration_too_long_for_instagram():
    asset = _make_video_asset(duration_seconds=120.0)
    warnings = _video_spec_warnings(asset)
    assert any("90" in w for w in warnings["instagram"])
    assert warnings["x"] == []


def test_spec_warnings_duration_too_short_for_linkedin():
    asset = _make_video_asset(duration_seconds=1.5)
    warnings = _video_spec_warnings(asset)
    assert any("3" in w for w in warnings["linkedin"])


def test_spec_warnings_wrong_aspect_for_tiktok():
    asset = _make_video_asset(width=1920, height=1080)  # landscape
    warnings = _video_spec_warnings(asset)
    assert any("9:16" in w for w in warnings["tiktok"])
    assert any("9:16" in w for w in warnings["instagram"])


def test_spec_warnings_mov_rejected_by_x():
    asset = _make_video_asset(mime_type="video/quicktime")
    warnings = _video_spec_warnings(asset)
    assert any("MP4" in w.upper() or "format" in w.lower() for w in warnings["x"])
    assert warnings["tiktok"] == []  # MOV is OK for TikTok


def test_spec_warnings_image_returns_empty():
    asset = _make_video_asset(mime_type="image/jpeg")
    warnings = _video_spec_warnings(asset)
    assert warnings == {}


# ── presign endpoint ───────────────────────────────────────────────────────────

def test_presign_video_mp4(client, auth_headers):
    with patch("src.backend.routers.media._r2_client") as mock_r2:
        mock_client = MagicMock()
        mock_client.generate_presigned_url.return_value = "https://presigned.example.com/upload"
        mock_r2.return_value = mock_client

        r = client.post(
            "/media/presign",
            json={"filename": "clip.mp4", "content_type": "video/mp4", "size_bytes": 5 * 1024 * 1024},
            headers=auth_headers,
        )
    assert r.status_code == 200
    data = r.json()
    assert data["media_asset_id"] > 0
    assert "upload_url" in data


def test_presign_video_exceeds_limit(client, auth_headers):
    r = client.post(
        "/media/presign",
        json={"filename": "huge.mp4", "content_type": "video/mp4", "size_bytes": 60 * 1024 * 1024},
        headers=auth_headers,
    )
    assert r.status_code == 422
    assert "50 MB" in r.json()["detail"]


def test_presign_unsupported_type(client, auth_headers):
    r = client.post(
        "/media/presign",
        json={"filename": "clip.avi", "content_type": "video/x-msvideo", "size_bytes": 1024},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_presign_image_still_works(client, auth_headers):
    with patch("src.backend.routers.media._r2_client") as mock_r2:
        mock_client = MagicMock()
        mock_client.generate_presigned_url.return_value = "https://presigned.example.com/upload"
        mock_r2.return_value = mock_client

        r = client.post(
            "/media/presign",
            json={"filename": "photo.jpg", "content_type": "image/jpeg", "size_bytes": 1 * 1024 * 1024},
            headers=auth_headers,
        )
    assert r.status_code == 200


# ── confirm + post_media ───────────────────────────────────────────────────────

def _create_asset(db, user_id: int, mime_type: str = "image/jpeg") -> models.MediaAsset:
    asset = models.MediaAsset(
        user_id=user_id,
        storage_key=f"users/{user_id}/media/test.jpg",
        public_url=f"https://cdn.example.com/users/{user_id}/media/test.jpg",
        original_filename="test.jpg",
        mime_type=mime_type,
        file_size_bytes=1024,
        status="uploaded",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def test_confirm_image_sets_ready(client, auth_headers):
    db = TestingSessionLocal()
    user = db.query(models.User).filter(models.User.email == "test@example.com").first()
    asset = _create_asset(db, user.id)
    db.close()

    with patch("src.backend.routers.media._r2_client") as mock_r2:
        mock_client = MagicMock()
        mock_r2.return_value = mock_client

        r = client.post(
            "/media/confirm",
            json={"media_asset_id": asset.id},
            headers=auth_headers,
        )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ready"
    assert data["spec_warnings"] is None


def test_confirm_video_triggers_processing_and_returns_warnings(client, auth_headers):
    db = TestingSessionLocal()
    user = db.query(models.User).filter(models.User.email == "test@example.com").first()
    asset = _create_asset(db, user.id, mime_type="video/mp4")
    db.close()

    with patch("src.backend.routers.media._r2_client") as mock_r2, \
         patch("src.backend.routers.media._process_video") as mock_proc:
        mock_client = MagicMock()
        mock_r2.return_value = mock_client

        r = client.post(
            "/media/confirm",
            json={"media_asset_id": asset.id},
            headers=auth_headers,
        )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ready"
    assert mock_proc.called
    assert "spec_warnings" in data
    assert isinstance(data["spec_warnings"], dict)


# ── post CRUD with media_ids ───────────────────────────────────────────────────

def test_create_post_with_media_ids(client, auth_headers):
    db = TestingSessionLocal()
    user = db.query(models.User).filter(models.User.email == "test@example.com").first()
    asset = _create_asset(db, user.id)
    db.close()

    r = client.post(
        "/posts",
        json={
            "title": "Video post",
            "caption": "Test",
            "platform": "instagram",
            "scheduled_date": "2026-07-01",
            "media_ids": [asset.id],
        },
        headers=auth_headers,
    )
    assert r.status_code == 201
    data = r.json()
    assert len(data["media_assets"]) == 1
    assert data["media_assets"][0]["id"] == asset.id


def test_create_post_with_multiple_media(client, auth_headers):
    db = TestingSessionLocal()
    user = db.query(models.User).filter(models.User.email == "test@example.com").first()
    a1 = _create_asset(db, user.id)
    a2 = _create_asset(db, user.id)
    a1_id, a2_id = a1.id, a2.id
    db.close()

    r = client.post(
        "/posts",
        json={
            "title": "Multi-media post",
            "caption": "Test",
            "platform": "instagram",
            "scheduled_date": "2026-07-02",
            "media_ids": [a1_id, a2_id],
        },
        headers=auth_headers,
    )
    assert r.status_code == 201
    data = r.json()
    assert len(data["media_assets"]) == 2


def test_create_post_without_media(client, auth_headers):
    r = client.post(
        "/posts",
        json={
            "title": "Text post",
            "caption": "No media",
            "platform": "x",
            "scheduled_date": "2026-07-03",
        },
        headers=auth_headers,
    )
    assert r.status_code == 201
    assert r.json()["media_assets"] == []


def test_update_post_replaces_media(client, auth_headers):
    db = TestingSessionLocal()
    user = db.query(models.User).filter(models.User.email == "test@example.com").first()
    a1 = _create_asset(db, user.id)
    a2 = _create_asset(db, user.id)
    a1_id, a2_id = a1.id, a2.id
    db.close()

    # Create with a1
    create_r = client.post(
        "/posts",
        json={
            "title": "Post",
            "caption": "",
            "platform": "instagram",
            "scheduled_date": "2026-07-04",
            "media_ids": [a1_id],
        },
        headers=auth_headers,
    )
    post_id = create_r.json()["id"]

    # Update to a2
    update_r = client.put(
        f"/posts/{post_id}",
        json={"media_ids": [a2_id]},
        headers=auth_headers,
    )
    assert update_r.status_code == 200
    data = update_r.json()
    assert len(data["media_assets"]) == 1
    assert data["media_assets"][0]["id"] == a2.id


def test_delete_post_cascades_post_media(client, auth_headers):
    db = TestingSessionLocal()
    user = db.query(models.User).filter(models.User.email == "test@example.com").first()
    asset = _create_asset(db, user.id)
    asset_id = asset.id
    db.close()

    create_r = client.post(
        "/posts",
        json={
            "title": "Delete me",
            "caption": "",
            "platform": "tiktok",
            "scheduled_date": "2026-07-05",
            "media_ids": [asset_id],
        },
        headers=auth_headers,
    )
    post_id = create_r.json()["id"]

    del_r = client.delete(f"/posts/{post_id}", headers=auth_headers)
    assert del_r.status_code == 204

    db2 = TestingSessionLocal()
    remaining = db2.query(models.PostMedia).filter(models.PostMedia.post_id == post_id).count()
    db2.close()
    assert remaining == 0
