# Image-Aware Captioning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `POST /ai/caption-from-image` that fetches a user's uploaded R2 image, downscales it with Pillow, sends it to Groq's Llama 4 Scout for vision captioning, and surfaces 3 captions + platform suggestion + alt text in the PostModal UI.

**Architecture:** Backend endpoint looks up the user's `MediaAsset`, fetches raw bytes from R2 via boto3, downscales with Pillow to ≤1568px long edge, encodes as base64 data-URL, then calls `llm.complete` (unchanged) with an OpenAI-compatible multimodal message. Frontend adds `AIImageCaptionButton` which appears only when a media asset is attached, shows clickable caption chips, and optionally auto-sets the platform if no explicit one was chosen.

**Tech Stack:** FastAPI, SQLAlchemy, boto3 (R2), Pillow, Groq via AsyncOpenAI compat, Next.js 14, React, TypeScript

---

### Task 1: Add Pillow to requirements.txt

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add Pillow**

Add to the end of `requirements.txt`:

```
Pillow>=10.0.0
```

- [ ] **Step 2: Install it locally**

```bash
pip install "Pillow>=10.0.0"
```

Expected: `Successfully installed Pillow-...` (or already satisfied)

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: add Pillow for image downscaling"
```

---

### Task 2: Add `_downscale_image` helper and `POST /ai/caption-from-image` endpoint

**Files:**
- Modify: `src/backend/routers/ai.py`

- [ ] **Step 1: Add imports at top of `src/backend/routers/ai.py`**

After the existing imports, add:

```python
import base64
import boto3
from src.backend.config import (
    R2_ACCOUNT_ID,
    R2_ACCESS_KEY_ID,
    R2_SECRET_ACCESS_KEY,
    R2_BUCKET,
)
```

The full import block at the top of the file should look like:

```python
import base64
import json
import boto3
from datetime import date, datetime
from typing import Optional, Union
from pydantic import BaseModel, field_validator, model_validator
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from src.backend import crud, models, schemas
from src.backend.auth import get_current_user
from src.backend.config import GROQ_API_KEY, R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET
from src.backend.database import get_db
from src.backend.limiter import limiter
```

- [ ] **Step 2: Add `_downscale_image` helper**

Add this function after the `_get_brand_voice_text` function (around line 284, before `_execute_tool`):

```python
def _downscale_image(image_bytes: bytes, mime_type: str | None) -> tuple[bytes, str]:
    from PIL import Image
    import io
    img = Image.open(io.BytesIO(image_bytes))
    w, h = img.size
    long_edge = max(w, h)
    if long_edge > 1568:
        scale = 1568 / long_edge
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    out_fmt = "JPEG"
    out_mime = "image/jpeg"
    if mime_type == "image/png":
        out_fmt, out_mime = "PNG", "image/png"
    elif mime_type == "image/webp":
        out_fmt, out_mime = "WEBP", "image/webp"
    if img.mode in ("RGBA", "P") and out_fmt == "JPEG":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format=out_fmt)
    return buf.getvalue(), out_mime
```

- [ ] **Step 3: Add `CaptionFromImageRequest` Pydantic model**

Add to the "Request/Response bodies" section (around line 234, after `ChatRequest`):

```python
class CaptionFromImageRequest(BaseModel):
    media_asset_id: int
    platform: Optional[str] = None
```

- [ ] **Step 4: Add the endpoint**

Add at the very end of `src/backend/routers/ai.py`, after the `/chat` endpoint:

```python
@router.post("/caption-from-image")
@limiter.limit("15/hour")
async def caption_from_image(
    request: Request,
    body: CaptionFromImageRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict:
    _require_groq()
    if body.platform and body.platform not in VALID_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Unknown platform: {body.platform}")

    asset = db.query(models.MediaAsset).filter(
        models.MediaAsset.id == body.media_asset_id,
        models.MediaAsset.user_id == current_user.id,
    ).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found")

    try:
        r2 = boto3.client(
            "s3",
            endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            region_name="auto",
        )
        obj = r2.get_object(Bucket=R2_BUCKET, Key=asset.storage_key)
        image_bytes = obj["Body"].read()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not fetch image from storage: {exc}")

    try:
        image_bytes, out_mime = _downscale_image(image_bytes, asset.mime_type)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not process image: {exc}")

    b64 = base64.b64encode(image_bytes).decode()
    data_url = f"data:{out_mime};base64,{b64}"

    bv_text = _get_brand_voice_text(db, current_user.id)
    platform_hint = f" for {body.platform}" if body.platform else ""

    system = (
        "You are an expert social media copywriter with vision capabilities.\n"
        "Analyze the attached image and write 3 captions.\n"
        "Respond ONLY with valid JSON, no prose, no markdown fences:\n"
        '{"suggested_platform":"instagram|x|tiktok|linkedin",'
        '"captions":["caption1","caption2","caption3"],'
        '"alt_text":"short accessibility description"}'
        f"{bv_text}"
    )
    messages = [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": data_url}},
                {"type": "text", "text": f"Write 3 captions for this image{platform_hint}. Return JSON only."},
            ],
        },
    ]

    from src.backend import llm
    try:
        result = await llm.complete(messages, max_tokens=1024)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")

    text = result["text"] or ""
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    try:
        parsed = json.loads(text)
    except Exception:
        parsed = {}

    suggested = parsed.get("suggested_platform", "")
    if suggested not in VALID_PLATFORMS:
        suggested = body.platform or "instagram"

    captions = parsed.get("captions", [])
    if not isinstance(captions, list):
        captions = []

    return {
        "suggested_platform": suggested,
        "captions": captions[:3],
        "alt_text": parsed.get("alt_text", ""),
    }
```

- [ ] **Step 5: Verify the file compiles**

```bash
cd /Users/big_meech/gigs/calendo && python -c "from src.backend.routers.ai import router; print('OK')"
```

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add src/backend/routers/ai.py
git commit -m "feat: add POST /ai/caption-from-image with Pillow downscaling"
```

---

### Task 3: Write backend tests for the new endpoint

**Files:**
- Create: `tests/test_ai_image_caption.py`

- [ ] **Step 1: Write the test file**

Create `tests/test_ai_image_caption.py` with this content:

```python
import io
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.backend import models
from tests.conftest import TestingSessionLocal


def _make_jpeg_bytes() -> bytes:
    """Create a minimal 100x100 red JPEG in memory."""
    from PIL import Image
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_large_jpeg_bytes() -> bytes:
    """Create a 2000x1000 JPEG to test downscaling."""
    from PIL import Image
    img = Image.new("RGB", (2000, 1000), color=(0, 128, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def media_asset(client, auth_headers):
    """Insert a media_asset row directly into the test DB and return it."""
    db = TestingSessionLocal()
    # Get the user id from a posts endpoint (user exists after auth_headers fixture)
    r = client.get("/posts", headers=auth_headers)
    assert r.status_code == 200

    # Look up the user by email
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
    mock_boto = MagicMock(return_value=mock_r2)
    return mock_boto


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
    # Falls back to the requested platform when suggested is invalid
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
    # Verify the image sent to LLM is smaller (base64 of downscaled < base64 of 2000x1000)
    call_args = mock_llm.call_args
    messages = call_args[0][0]
    user_content = messages[1]["content"]
    data_url = user_content[0]["image_url"]["url"]
    b64_part = data_url.split(",", 1)[1]
    sent_bytes = len(b64_part) * 3 // 4  # approx decoded size
    # Original 2000x1000 JPEG would be much larger than downscaled 1568x784
    original_size = len(large_jpeg)
    assert sent_bytes < original_size * 1.1  # may be smaller after downscale
```

- [ ] **Step 2: Run the tests to verify they fail (since endpoint not implemented yet)**

Wait — the endpoint IS already implemented by Task 2, so these should PASS. Run:

```bash
cd /Users/big_meech/gigs/calendo && python -m pytest tests/test_ai_image_caption.py -v
```

Expected: All 9 tests PASS (with GROQ_API_KEY env var check skipped via mock).

Note: If `GROQ_API_KEY` is missing, tests that don't mock it will get 503. The `_require_groq()` check runs before auth in some code paths. If needed, set `GROQ_API_KEY=test` in the test or mock it. Add this to the top of the test file if tests fail with 503:

```python
import os
os.environ.setdefault("GROQ_API_KEY", "test-key-for-tests")
```

- [ ] **Step 3: Commit**

```bash
git add tests/test_ai_image_caption.py
git commit -m "test: add backend tests for caption-from-image endpoint"
```

---

### Task 4: Add `captionFromImage` to the frontend AI service

**Files:**
- Modify: `src/frontend/services/ai.ts`

- [ ] **Step 1: Add the export function at the end of `src/frontend/services/ai.ts`**

Append to the end of the file:

```typescript
export async function captionFromImage(
  mediaAssetId: number,
  platform?: string,
): Promise<{ suggested_platform: string; captions: string[]; alt_text: string }> {
  const res = await fetch(`${API_BASE}/ai/caption-from-image`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ media_asset_id: mediaAssetId, platform: platform ?? null }),
  })
  return handleResponse(res)
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /Users/big_meech/gigs/calendo/src/frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: No errors (or only pre-existing errors unrelated to this change).

- [ ] **Step 3: Commit**

```bash
git add src/frontend/services/ai.ts
git commit -m "feat: add captionFromImage service function"
```

---

### Task 5: Create `AIImageCaptionButton` component

**Files:**
- Create: `src/frontend/components/AIImageCaptionButton.tsx`

- [ ] **Step 1: Create the component file**

Create `src/frontend/components/AIImageCaptionButton.tsx`:

```tsx
"use client"
import * as React from "react"
import { Sparkles } from "lucide-react"
import { captionFromImage } from "@/services/ai"

const PLATFORM_LABELS: Record<string, string> = {
  instagram: "Instagram",
  x: "X",
  tiktok: "TikTok",
  linkedin: "LinkedIn",
}

interface AIImageCaptionButtonProps {
  mediaAssetId: number
  platform: string | null
  disabled?: boolean
  onSelectCaption: (caption: string) => void
  onSelectPlatform: (platform: string) => void
}

interface CaptionResult {
  suggested_platform: string
  captions: string[]
  alt_text: string
}

export function AIImageCaptionButton({
  mediaAssetId,
  platform,
  disabled,
  onSelectCaption,
  onSelectPlatform,
}: AIImageCaptionButtonProps) {
  const [loading, setLoading] = React.useState(false)
  const [result, setResult] = React.useState<CaptionResult | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const calledWithPlatform = React.useRef<string | null>(null)

  const handleGenerate = async () => {
    setLoading(true)
    setError(null)
    setResult(null)
    calledWithPlatform.current = platform
    try {
      const data = await captionFromImage(mediaAssetId, platform ?? undefined)
      setResult(data)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to generate captions")
    } finally {
      setLoading(false)
    }
  }

  const handleSelect = (caption: string) => {
    onSelectCaption(caption)
    if (!calledWithPlatform.current && result) {
      onSelectPlatform(result.suggested_platform)
    }
    setResult(null)
  }

  return (
    <div className="flex flex-col gap-2">
      <button
        type="button"
        onClick={handleGenerate}
        disabled={disabled || loading}
        className="flex items-center gap-1.5 self-start rounded-md border px-3 py-1.5 text-xs font-medium transition-colors hover:border-[#E1306C] hover:text-[#E1306C] disabled:cursor-not-allowed disabled:opacity-50"
        style={{ backgroundColor: "transparent", borderColor: "#2A2A2A", color: "#888888" }}
      >
        <Sparkles size={12} />
        {loading ? "Analyzing image…" : "✨ Caption this image"}
      </button>

      {error && (
        <p className="text-xs" style={{ color: "#E1306C" }}>
          {error}
        </p>
      )}

      {result && (
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <span
              className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
              style={{ backgroundColor: "#E1306C22", color: "#E1306C", border: "1px solid #E1306C44" }}
            >
              {PLATFORM_LABELS[result.suggested_platform] ?? result.suggested_platform}
            </span>
            {result.alt_text && (
              <span className="text-xs truncate max-w-[200px]" style={{ color: "#555555" }} title={result.alt_text}>
                {result.alt_text}
              </span>
            )}
          </div>
          <p className="text-xs" style={{ color: "#888888" }}>
            Click a caption to use it:
          </p>
          {result.captions.map((caption, i) => (
            <button
              key={i}
              type="button"
              onClick={() => handleSelect(caption)}
              className="w-full rounded-md border px-3 py-2 text-left text-xs transition-colors hover:border-[#E1306C]"
              style={{
                backgroundColor: "#0F0F0F",
                borderColor: "#2A2A2A",
                color: "#F5F5F5",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {caption}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /Users/big_meech/gigs/calendo/src/frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: No new errors.

- [ ] **Step 3: Commit**

```bash
git add src/frontend/components/AIImageCaptionButton.tsx
git commit -m "feat: add AIImageCaptionButton component for image-aware captioning"
```

---

### Task 6: Wire `AIImageCaptionButton` into `PostModal.tsx`

**Files:**
- Modify: `src/frontend/components/PostModal.tsx`

The goal: Show `AIImageCaptionButton` below the caption textarea when `mediaAssetId` is set (and not published). It replaces or sits alongside the existing `AICaptionButton`.

Per the spec, the image caption button appears "once an image is attached". When no image is attached, the existing text-based `AICaptionButton` should still be shown.

- [ ] **Step 1: Add the import**

In `src/frontend/components/PostModal.tsx`, add after the existing `AICaptionButton` import line:

```tsx
import { AIImageCaptionButton } from "@/components/AIImageCaptionButton"
```

So the import block looks like:

```tsx
import { AICaptionButton } from "@/components/AICaptionButton"
import { AIImageCaptionButton } from "@/components/AIImageCaptionButton"
import { MediaUploader } from "@/components/MediaUploader"
```

- [ ] **Step 2: Replace the caption AI section**

Find the existing block inside `PostModal` (around line 261–267):

```tsx
            {!isPublished && (
              <AICaptionButton
                platform={mode === "create" ? selectedPlatforms[0] : platform}
                idea={title.trim() || caption.trim()}
                disabled={isPublished}
                onSelectCaption={setCaption}
              />
            )}
```

Replace it with:

```tsx
            {!isPublished && (
              mediaAssetId ? (
                <AIImageCaptionButton
                  mediaAssetId={mediaAssetId}
                  platform={mode === "create" ? selectedPlatforms[0] : platform}
                  disabled={isPublished}
                  onSelectCaption={setCaption}
                  onSelectPlatform={(p) => {
                    if (mode === "create") {
                      setSelectedPlatforms([p as Platform])
                    } else {
                      setPlatform(p as Platform)
                    }
                  }}
                />
              ) : (
                <AICaptionButton
                  platform={mode === "create" ? selectedPlatforms[0] : platform}
                  idea={title.trim() || caption.trim()}
                  disabled={isPublished}
                  onSelectCaption={setCaption}
                />
              )
            )}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /Users/big_meech/gigs/calendo/src/frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: No new errors.

- [ ] **Step 4: Commit**

```bash
git add src/frontend/components/PostModal.tsx
git commit -m "feat: show AIImageCaptionButton in PostModal when image is attached"
```

---

### Task 7: Run full test suite and verify

- [ ] **Step 1: Run all backend tests**

```bash
cd /Users/big_meech/gigs/calendo && GROQ_API_KEY=test python -m pytest tests/ -v 2>&1
```

Expected: All tests pass. If `test_ai_image_caption.py` tests fail with 503, add `os.environ.setdefault("GROQ_API_KEY", "test")` at the top of that file.

- [ ] **Step 2: Build the frontend**

```bash
cd /Users/big_meech/gigs/calendo/src/frontend && npm run build 2>&1 | tail -20
```

Expected: Build succeeds, no TypeScript or lint errors.

- [ ] **Step 3: Final commit if any fixups were needed**

```bash
git add -p
git commit -m "fix: test and build fixups for image captioning"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] `POST /ai/caption-from-image` with `media_asset_id` + optional `platform` → Task 2
- [x] 404 if asset not found or belongs to another user → Task 2 endpoint
- [x] Fetch image from R2 → Task 2 endpoint
- [x] Downscale with Pillow to max 1568px long edge → `_downscale_image` helper
- [x] Send via `app/llm.py` as OpenAI-compatible multimodal message → Task 2
- [x] Inject brand voice if present → `_get_brand_voice_text` called in endpoint
- [x] Return `{suggested_platform, captions[3], alt_text}` → Task 2
- [x] Strip fences before JSON.parse → Task 2 parsing block
- [x] Validate `suggested_platform`, fall back gracefully → Task 2 parsing block
- [x] Rate limit 15/hour → `@limiter.limit("15/hour")`
- [x] Add Pillow to requirements.txt → Task 1
- [x] No DB migration (reuses media_asset) → confirmed, no Alembic changes
- [x] Frontend: show "✨ Caption this image" when image attached → Task 6
- [x] Frontend: call endpoint with selected platform → Task 6
- [x] Frontend: render suggested_platform as badge → Task 5 (AIImageCaptionButton)
- [x] Frontend: 3 captions as clickable chips → Task 5
- [x] Frontend: alt_text shown subtly → Task 5
- [x] Frontend: choosing chip sets suggested platform if no platform hint was sent → Task 5 `handleSelect`
- [x] Loading + error states themed with tokens → Task 5

**Placeholder scan:** None found — all code blocks are complete.

**Type consistency:**
- `captionFromImage` in `services/ai.ts` returns `{ suggested_platform, captions, alt_text }` ✓
- `AIImageCaptionButton` uses `CaptionResult` type with same shape ✓
- `onSelectPlatform` callback receives `string`, PostModal casts to `Platform` ✓
- `_downscale_image` returns `tuple[bytes, str]` and endpoint uses it correctly ✓
