import json
import os
from datetime import date
os.environ.setdefault("GROQ_API_KEY", "test-key-for-tests")

from unittest.mock import AsyncMock, patch

import pytest

from src.backend import models
from tests.conftest import TestingSessionLocal


def _user_id(client, auth_headers) -> int:
    client.get("/posts", headers=auth_headers)
    db = TestingSessionLocal()
    user = db.query(models.User).filter(models.User.email == "test@example.com").first()
    assert user is not None
    uid = user.id
    db.close()
    return uid


@pytest.fixture
def media_asset(client, auth_headers):
    uid = _user_id(client, auth_headers)
    db = TestingSessionLocal()
    asset = models.MediaAsset(
        user_id=uid,
        storage_key="users/1/media/summer-launch.jpg",
        public_url="https://example.com/summer-launch.jpg",
        original_filename="summer-launch.jpg",
        mime_type="image/jpeg",
        file_size_bytes=1024,
        status="ready",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    asset_id = asset.id
    db.close()
    return asset_id


@pytest.fixture
def media_asset_on_post(client, auth_headers, media_asset):
    """Asset attached to a post, so the endpoint has real text context to work from."""
    uid = _user_id(client, auth_headers)
    db = TestingSessionLocal()
    post = models.Post(
        user_id=uid,
        title="Spring collection teaser",
        caption="Something new is coming",
        platform="instagram",
        scheduled_date=date(2026, 5, 1),
        notes="Keep it playful",
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    db.add(models.PostMedia(post_id=post.id, media_id=media_asset, position=0))
    db.commit()
    db.close()
    return media_asset


_GOOD_LLM_RESPONSE = json.dumps({
    "suggested_platform": "instagram",
    "captions": ["Caption one", "Caption two", "Caption three"],
    "alt_text": "A red square",
})


def _llm_mock(text: str = _GOOD_LLM_RESPONSE) -> AsyncMock:
    return AsyncMock(return_value={"text": text, "tool_calls": [], "finish_reason": "stop"})


def test_caption_from_image_success(client, auth_headers, media_asset):
    with patch("src.backend.llm.complete", new=_llm_mock()):
        r = client.post(
            "/ai/caption-from-image",
            json={"media_asset_id": media_asset, "platform": "instagram"},
            headers=auth_headers,
        )

    assert r.status_code == 200
    data = r.json()
    assert data["suggested_platform"] == "instagram"
    assert len(data["captions"]) == 3
    assert data["captions"][0] == "Caption one"
    assert data["alt_text"] == "A red square"


def test_caption_from_image_no_platform_hint(client, auth_headers, media_asset):
    with patch("src.backend.llm.complete", new=_llm_mock()) as mock_llm:
        r = client.post(
            "/ai/caption-from-image",
            json={"media_asset_id": media_asset},
            headers=auth_headers,
        )

    assert r.status_code == 200
    data = r.json()
    assert data["suggested_platform"] in {"instagram", "x", "tiktok", "linkedin", "facebook"}
    assert len(data["captions"]) == 3
    first_line = mock_llm.call_args[0][0][1]["content"].split("\n")[0]
    assert not any(p in first_line for p in {"instagram", "x", "tiktok", "linkedin", "facebook"})


def test_caption_from_image_platform_hint_is_sent(client, auth_headers, media_asset):
    with patch("src.backend.llm.complete", new=_llm_mock()) as mock_llm:
        r = client.post(
            "/ai/caption-from-image",
            json={"media_asset_id": media_asset, "platform": "linkedin"},
            headers=auth_headers,
        )

    assert r.status_code == 200
    assert "for linkedin" in mock_llm.call_args[0][0][1]["content"]


def test_caption_from_image_404_wrong_user(client, auth_headers):
    r = client.post(
        "/ai/caption-from-image",
        json={"media_asset_id": 99999},
        headers=auth_headers,
    )
    assert r.status_code == 404


def test_caption_from_image_unauthenticated(client, media_asset):
    r = client.post(
        "/ai/caption-from-image",
        json={"media_asset_id": media_asset},
    )
    assert r.status_code == 403


def test_caption_from_image_invalid_platform(client, auth_headers, media_asset):
    r = client.post(
        "/ai/caption-from-image",
        json={"media_asset_id": media_asset, "platform": "myspace"},
        headers=auth_headers,
    )
    assert r.status_code == 400


def test_caption_from_image_sends_no_image_to_model(client, auth_headers, media_asset):
    """The model is text-only: no image_url block, no base64 payload."""
    with patch("src.backend.llm.complete", new=_llm_mock()) as mock_llm:
        r = client.post(
            "/ai/caption-from-image",
            json={"media_asset_id": media_asset, "platform": "instagram"},
            headers=auth_headers,
        )

    assert r.status_code == 200
    messages = mock_llm.call_args[0][0]
    system, user = messages[0]["content"], messages[1]["content"]
    assert isinstance(user, str)
    assert "image_url" not in user and "base64" not in user
    assert "vision" not in system.lower()
    assert "cannot see the image" in system


def test_caption_from_image_uses_post_text_context(client, auth_headers, media_asset_on_post):
    with patch("src.backend.llm.complete", new=_llm_mock()) as mock_llm:
        r = client.post(
            "/ai/caption-from-image",
            json={"media_asset_id": media_asset_on_post, "platform": "instagram"},
            headers=auth_headers,
        )

    assert r.status_code == 200
    user_content = mock_llm.call_args[0][0][1]["content"]
    assert "Spring collection teaser" in user_content
    assert "Something new is coming" in user_content
    assert "Keep it playful" in user_content
    assert "summer launch" in user_content


def test_caption_from_image_works_when_image_unavailable(client, auth_headers):
    """Storage is never touched, so an asset whose bytes are gone still yields captions."""
    uid = _user_id(client, auth_headers)
    db = TestingSessionLocal()
    asset = models.MediaAsset(
        user_id=uid,
        storage_key="users/1/media/deleted-object.bin",
        original_filename=None,
        mime_type=None,
        status="ready",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    asset_id = asset.id
    db.close()

    with patch("src.backend.llm.complete", new=_llm_mock()):
        r = client.post(
            "/ai/caption-from-image",
            json={"media_asset_id": asset_id, "platform": "x"},
            headers=auth_headers,
        )

    assert r.status_code == 200
    assert len(r.json()["captions"]) == 3


def test_caption_from_image_llm_returns_fenced_json(client, auth_headers, media_asset):
    fenced = "```json\n" + _GOOD_LLM_RESPONSE + "\n```"

    with patch("src.backend.llm.complete", new=_llm_mock(fenced)):
        r = client.post(
            "/ai/caption-from-image",
            json={"media_asset_id": media_asset, "platform": "instagram"},
            headers=auth_headers,
        )

    assert r.status_code == 200
    assert r.json()["captions"][0] == "Caption one"


def test_caption_from_image_invalid_suggested_platform_fallback(client, auth_headers, media_asset):
    bad_json = json.dumps({
        "suggested_platform": "myspace",
        "captions": ["Cap 1", "Cap 2", "Cap 3"],
        "alt_text": "test",
    })

    with patch("src.backend.llm.complete", new=_llm_mock(bad_json)):
        r = client.post(
            "/ai/caption-from-image",
            json={"media_asset_id": media_asset, "platform": "linkedin"},
            headers=auth_headers,
        )

    assert r.status_code == 200
    assert r.json()["suggested_platform"] == "linkedin"
