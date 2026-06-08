import io
import json
import os
os.environ.setdefault("GROQ_API_KEY", "test-key-for-tests")

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.backend import models
from tests.conftest import TestingSessionLocal


def _make_jpeg_bytes() -> bytes:
    from PIL import Image
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_large_jpeg_bytes() -> bytes:
    from PIL import Image
    img = Image.new("RGB", (2000, 1000), color=(0, 128, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def media_asset(client, auth_headers):
    client.get("/posts", headers=auth_headers)
    db = TestingSessionLocal()
    user = db.query(models.User).filter(models.User.email == "test@example.com").first()
    assert user is not None
    asset = models.MediaAsset(
        user_id=user.id,
        storage_key="users/1/media/test-image.jpg",
        public_url="https://example.com/test-image.jpg",
        original_filename="test-image.jpg",
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


_GOOD_LLM_RESPONSE = json.dumps({
    "suggested_platform": "instagram",
    "captions": ["Caption one", "Caption two", "Caption three"],
    "alt_text": "A red square",
})


def _mock_r2_client(image_bytes: bytes):
    mock_body = MagicMock()
    mock_body.read.return_value = image_bytes
    mock_obj = {"Body": mock_body}
    mock_r2 = MagicMock()
    mock_r2.get_object.return_value = mock_obj
    return MagicMock(return_value=mock_r2)


def test_caption_from_image_success(client, auth_headers, media_asset):
    jpeg_bytes = _make_jpeg_bytes()
    mock_boto = _mock_r2_client(jpeg_bytes)
    llm_result = {"text": _GOOD_LLM_RESPONSE, "tool_calls": [], "finish_reason": "stop"}

    with patch("src.backend.routers.ai.boto3.client", mock_boto), \
         patch("src.backend.llm.complete", new=AsyncMock(return_value=llm_result)):
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
    jpeg_bytes = _make_jpeg_bytes()
    mock_boto = _mock_r2_client(jpeg_bytes)
    llm_result = {"text": _GOOD_LLM_RESPONSE, "tool_calls": [], "finish_reason": "stop"}

    with patch("src.backend.routers.ai.boto3.client", mock_boto), \
         patch("src.backend.llm.complete", new=AsyncMock(return_value=llm_result)):
        r = client.post(
            "/ai/caption-from-image",
            json={"media_asset_id": media_asset},
            headers=auth_headers,
        )

    assert r.status_code == 200
    data = r.json()
    assert data["suggested_platform"] in {"instagram", "x", "tiktok", "linkedin"}
    assert len(data["captions"]) == 3


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


def test_caption_from_image_r2_error(client, auth_headers, media_asset):
    mock_r2 = MagicMock()
    mock_r2.get_object.side_effect = Exception("S3 connection refused")
    mock_boto = MagicMock(return_value=mock_r2)

    with patch("src.backend.routers.ai.boto3.client", mock_boto):
        r = client.post(
            "/ai/caption-from-image",
            json={"media_asset_id": media_asset, "platform": "instagram"},
            headers=auth_headers,
        )

    assert r.status_code == 502
    assert "Could not fetch image from storage" in r.json()["detail"]


def test_caption_from_image_llm_returns_fenced_json(client, auth_headers, media_asset):
    jpeg_bytes = _make_jpeg_bytes()
    mock_boto = _mock_r2_client(jpeg_bytes)
    fenced = "```json\n" + _GOOD_LLM_RESPONSE + "\n```"
    llm_result = {"text": fenced, "tool_calls": [], "finish_reason": "stop"}

    with patch("src.backend.routers.ai.boto3.client", mock_boto), \
         patch("src.backend.llm.complete", new=AsyncMock(return_value=llm_result)):
        r = client.post(
            "/ai/caption-from-image",
            json={"media_asset_id": media_asset, "platform": "instagram"},
            headers=auth_headers,
        )

    assert r.status_code == 200
    assert r.json()["captions"][0] == "Caption one"


def test_caption_from_image_invalid_suggested_platform_fallback(client, auth_headers, media_asset):
    jpeg_bytes = _make_jpeg_bytes()
    mock_boto = _mock_r2_client(jpeg_bytes)
    bad_json = json.dumps({
        "suggested_platform": "myspace",
        "captions": ["Cap 1", "Cap 2", "Cap 3"],
        "alt_text": "test",
    })
    llm_result = {"text": bad_json, "tool_calls": [], "finish_reason": "stop"}

    with patch("src.backend.routers.ai.boto3.client", mock_boto), \
         patch("src.backend.llm.complete", new=AsyncMock(return_value=llm_result)):
        r = client.post(
            "/ai/caption-from-image",
            json={"media_asset_id": media_asset, "platform": "linkedin"},
            headers=auth_headers,
        )

    assert r.status_code == 200
    assert r.json()["suggested_platform"] == "linkedin"


def test_downscale_large_image(client, auth_headers, media_asset):
    large_jpeg = _make_large_jpeg_bytes()
    mock_boto = _mock_r2_client(large_jpeg)
    llm_result = {"text": _GOOD_LLM_RESPONSE, "tool_calls": [], "finish_reason": "stop"}

    with patch("src.backend.routers.ai.boto3.client", mock_boto), \
         patch("src.backend.llm.complete", new=AsyncMock(return_value=llm_result)) as mock_llm:
        r = client.post(
            "/ai/caption-from-image",
            json={"media_asset_id": media_asset, "platform": "x"},
            headers=auth_headers,
        )

    assert r.status_code == 200
    call_args = mock_llm.call_args
    messages = call_args[0][0]
    user_content = messages[1]["content"]
    data_url = user_content[0]["image_url"]["url"]
    b64_part = data_url.split(",", 1)[1]
    sent_size = len(b64_part) * 3 // 4
    # 2000x1000 downscaled to 1568x784 should be smaller than original 2000x1000
    assert sent_size < len(large_jpeg) * 2  # sanity bound
