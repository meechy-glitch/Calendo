# Media Library on R2 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add presigned-upload media support backed by Cloudflare R2 — files never pass through the server — with drag/drop frontend uploader and thumbnail display in calendar and post form.

**Architecture:** Client calls `/media/presign` to get a presigned R2 PUT URL and create a `media_asset` row, PUTs the file directly to R2 via XHR (with progress), then calls `/media/confirm` to verify and activate the asset. Posts carry an optional `media_asset_id` FK. Frontend shows thumbnails in the calendar chips and post modal.

**Tech Stack:** Python/FastAPI (boto3 for R2), SQLAlchemy 2.0 + Alembic, Next.js 14 App Router (TypeScript), existing design tokens

---

## File Map

**Create:**
- `src/backend/r2.py` — boto3 client factory + `generate_presigned_put` + `object_exists`
- `src/backend/routers/media.py` — `/media/presign` and `/media/confirm` endpoints
- `src/frontend/services/media.ts` — `presign()` and `confirm()` API calls
- `src/frontend/components/MediaUploader.tsx` — drag/drop + XHR progress bar
- `alembic/versions/005_add_media_assets.py` — migration
- `tests/test_media.py` — backend media endpoint tests

**Modify:**
- `requirements.txt` — add boto3, aioboto3
- `src/backend/config.py` — add R2_* env vars
- `src/backend/models.py` — `MediaAsset` model, `media_asset_id` FK on `Post`, `media_public_url` property
- `src/backend/schemas.py` — `PresignRequest`, `PresignResponse`, `ConfirmRequest`, `MediaAssetResponse`; update `PostCreate`, `PostUpdate`, `PostResponse`
- `src/backend/main.py` — include media router
- `src/frontend/components/PostModal.tsx` — add media section, update `PostData`
- `src/frontend/components/CalendarGrid.tsx` — update `Post` interface, `PostChip` thumbnail
- `src/frontend/app/dashboard/page.tsx` — thread `media_asset_id` / `media_public_url` through `ApiPost`, `toCalendarPost`, `handlePostClick`, `handleSave`

---

### Task 1: Add dependencies and R2 env config

**Files:**
- Modify: `requirements.txt`
- Modify: `src/backend/config.py`

- [ ] **Step 1: Add boto3 and aioboto3 to requirements.txt**

Open `requirements.txt` and add these two lines after `openai>=1.30.0`:

```
boto3==1.34.0
aioboto3==13.0.0
```

- [ ] **Step 2: Add R2 env vars to config.py**

Open `src/backend/config.py`. After the `GROQ_API_KEY` line, add:

```python
R2_ACCOUNT_ID: str = os.getenv("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID: str = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY: str = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET: str = os.getenv("R2_BUCKET", "")
R2_PUBLIC_BASE_URL: str = os.getenv("R2_PUBLIC_BASE_URL", "")
```

- [ ] **Step 3: Install the new deps**

```bash
cd /Users/big_meech/gigs/calendo && source venv/bin/activate && pip install boto3==1.34.0 aioboto3==13.0.0
```

Expected: both packages install without errors.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt src/backend/config.py
git commit -m "chore: add boto3/aioboto3 deps and R2 env vars"
```

---

### Task 2: R2 helper module

**Files:**
- Create: `src/backend/r2.py`

- [ ] **Step 1: Create `src/backend/r2.py`**

```python
import boto3
from botocore.exceptions import ClientError
from src.backend.config import (
    R2_ACCOUNT_ID,
    R2_ACCESS_KEY_ID,
    R2_SECRET_ACCESS_KEY,
    R2_BUCKET,
)

EXPIRES_IN = 3600


def get_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )


def generate_presigned_put(storage_key: str, content_type: str) -> str:
    client = get_r2_client()
    return client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": R2_BUCKET,
            "Key": storage_key,
            "ContentType": content_type,
        },
        ExpiresIn=EXPIRES_IN,
    )


def object_exists(storage_key: str) -> bool:
    client = get_r2_client()
    try:
        client.head_object(Bucket=R2_BUCKET, Key=storage_key)
        return True
    except ClientError:
        return False
```

- [ ] **Step 2: Verify import works**

```bash
cd /Users/big_meech/gigs/calendo && source venv/bin/activate && python -c "from src.backend.r2 import generate_presigned_put, object_exists; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add src/backend/r2.py
git commit -m "feat: add R2 boto3 helper module"
```

---

### Task 3: MediaAsset model and Post FK

**Files:**
- Modify: `src/backend/models.py`

- [ ] **Step 1: Add BigInteger import and MediaAsset model to models.py**

Open `src/backend/models.py`. Change the import line from:

```python
from sqlalchemy import Boolean, Column, Integer, String, DateTime, Date, ForeignKey, Enum
```

to:

```python
from sqlalchemy import Boolean, Column, Integer, BigInteger, String, Text, DateTime, Date, ForeignKey, Enum
```

Then add the `MediaAsset` class after the `BrandVoice` class (before `PasswordResetToken`):

```python
class MediaAsset(Base):
    __tablename__ = "media_asset"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    storage_key = Column(Text, nullable=False)
    provider = Column(String, default="r2")
    public_url = Column(Text, nullable=True)
    original_filename = Column(Text, nullable=True)
    mime_type = Column(String, nullable=True)
    file_size_bytes = Column(BigInteger, nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    status = Column(String, default="uploaded")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="media_assets")
```

- [ ] **Step 2: Add media_asset_id FK and media_public_url property to Post**

In `src/backend/models.py`, inside the `Post` class, add after the `updated_at` line:

```python
    media_asset_id = Column(Integer, ForeignKey("media_asset.id"), nullable=True)
    media_asset = relationship("MediaAsset", foreign_keys=[media_asset_id])

    @property
    def media_public_url(self) -> str | None:
        return self.media_asset.public_url if self.media_asset else None
```

- [ ] **Step 3: Add media_assets relationship to User**

In the `User` class, add after the `brand_voice` relationship line:

```python
    media_assets = relationship("MediaAsset", back_populates="user")
```

- [ ] **Step 4: Verify models import**

```bash
cd /Users/big_meech/gigs/calendo && source venv/bin/activate && python -c "from src.backend.models import MediaAsset, Post, User; print('ok')"
```

Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add src/backend/models.py
git commit -m "feat: add MediaAsset model and media_asset_id FK on posts"
```

---

### Task 4: Alembic migration 005

**Files:**
- Create: `alembic/versions/005_add_media_assets.py`

- [ ] **Step 1: Create migration file `alembic/versions/005_add_media_assets.py`**

```python
"""Add media_asset table and posts.media_asset_id

Revision ID: 005
Revises: 004
Create Date: 2026-06-05 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "media_asset",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(), nullable=True, server_default="r2"),
        sa.Column("public_url", sa.Text(), nullable=True),
        sa.Column("original_filename", sa.Text(), nullable=True),
        sa.Column("mime_type", sa.String(), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=True, server_default="uploaded"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_media_asset_id"), "media_asset", ["id"], unique=False)
    op.add_column("posts", sa.Column("media_asset_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_posts_media_asset_id",
        "posts",
        "media_asset",
        ["media_asset_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_posts_media_asset_id", "posts", type_="foreignkey")
    op.drop_column("posts", "media_asset_id")
    op.drop_index(op.f("ix_media_asset_id"), table_name="media_asset")
    op.drop_table("media_asset")
```

- [ ] **Step 2: Verify alembic can see the migration**

```bash
cd /Users/big_meech/gigs/calendo && source venv/bin/activate && alembic heads
```

Expected: `005 (head)`

- [ ] **Step 3: Commit**

```bash
git add alembic/versions/005_add_media_assets.py
git commit -m "feat: alembic migration 005 — media_asset table and posts FK"
```

---

### Task 5: Media schemas

**Files:**
- Modify: `src/backend/schemas.py`

- [ ] **Step 1: Add media schemas and update PostCreate/PostUpdate/PostResponse**

Open `src/backend/schemas.py`. At the top, the `Optional` import is already present. Add these classes at the end of the file:

```python
class PresignRequest(BaseModel):
    filename: str
    content_type: str
    size_bytes: int


class PresignResponse(BaseModel):
    upload_url: str
    media_asset_id: int
    storage_key: str
    public_url: str
    expires_in: int


class ConfirmRequest(BaseModel):
    media_asset_id: int


class MediaAssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    storage_key: str
    public_url: Optional[str] = None
    original_filename: Optional[str] = None
    mime_type: Optional[str] = None
    file_size_bytes: Optional[int] = None
    status: str
```

- [ ] **Step 2: Update PostCreate to accept optional media_asset_id**

In the `PostCreate` class, add after `notes`:

```python
    media_asset_id: Optional[int] = None
```

- [ ] **Step 3: Update PostUpdate to accept optional media_asset_id**

In the `PostUpdate` class, add after `notes`:

```python
    media_asset_id: Optional[int] = None
```

- [ ] **Step 4: Update PostResponse to include media fields**

In the `PostResponse` class, add after `updated_at`:

```python
    media_asset_id: Optional[int] = None
    media_public_url: Optional[str] = None
```

- [ ] **Step 5: Verify schemas import**

```bash
cd /Users/big_meech/gigs/calendo && source venv/bin/activate && python -c "from src.backend.schemas import PresignRequest, PresignResponse, ConfirmRequest, MediaAssetResponse; print('ok')"
```

Expected: `ok`

- [ ] **Step 6: Commit**

```bash
git add src/backend/schemas.py
git commit -m "feat: add media schemas and media_asset_id to post schemas"
```

---

### Task 6: Write failing backend tests for media endpoints

**Files:**
- Create: `tests/test_media.py`

- [ ] **Step 1: Create `tests/test_media.py`**

```python
from unittest.mock import patch

PRESIGN_DATA = {
    "filename": "photo.jpg",
    "content_type": "image/jpeg",
    "size_bytes": 100 * 1024,
}


def test_presign_happy_path(client, auth_headers):
    with patch("src.backend.routers.media.generate_presigned_put") as mock_presign:
        mock_presign.return_value = "https://r2.example.com/presigned"
        r = client.post("/media/presign", json=PRESIGN_DATA, headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["upload_url"] == "https://r2.example.com/presigned"
    assert "media_asset_id" in data
    assert isinstance(data["media_asset_id"], int)
    assert "public_url" in data
    assert data["expires_in"] == 3600


def test_presign_invalid_mime(client, auth_headers):
    data = {**PRESIGN_DATA, "content_type": "image/gif"}
    r = client.post("/media/presign", json=data, headers=auth_headers)
    assert r.status_code == 422
    assert "Unsupported" in r.json()["detail"]


def test_presign_file_too_large(client, auth_headers):
    data = {**PRESIGN_DATA, "size_bytes": 9 * 1024 * 1024}
    r = client.post("/media/presign", json=data, headers=auth_headers)
    assert r.status_code == 422
    assert "too large" in r.json()["detail"]


def test_presign_unauthenticated(client):
    r = client.post("/media/presign", json=PRESIGN_DATA)
    assert r.status_code == 403


def _create_asset(client, auth_headers) -> int:
    with patch("src.backend.routers.media.generate_presigned_put") as mock:
        mock.return_value = "https://r2.example.com/presigned"
        r = client.post("/media/presign", json=PRESIGN_DATA, headers=auth_headers)
    return r.json()["media_asset_id"]


def test_confirm_happy_path(client, auth_headers):
    asset_id = _create_asset(client, auth_headers)
    with patch("src.backend.routers.media.object_exists") as mock_exists:
        mock_exists.return_value = True
        r = client.post("/media/confirm", json={"media_asset_id": asset_id}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "ready"


def test_confirm_object_not_in_r2(client, auth_headers):
    asset_id = _create_asset(client, auth_headers)
    with patch("src.backend.routers.media.object_exists") as mock_exists:
        mock_exists.return_value = False
        r = client.post("/media/confirm", json={"media_asset_id": asset_id}, headers=auth_headers)
    assert r.status_code == 422
    assert "not found in storage" in r.json()["detail"]


def test_confirm_asset_not_found(client, auth_headers):
    with patch("src.backend.routers.media.object_exists"):
        r = client.post("/media/confirm", json={"media_asset_id": 99999}, headers=auth_headers)
    assert r.status_code == 404


def test_confirm_wrong_user(client, auth_headers):
    asset_id = _create_asset(client, auth_headers)

    client.post("/auth/register", json={"email": "user2@example.com", "password": "password123"})
    login_r = client.post("/auth/login", json={"email": "user2@example.com", "password": "password123"})
    user2_headers = {"Authorization": f"Bearer {login_r.json()['access_token']}"}

    with patch("src.backend.routers.media.object_exists") as mock_exists:
        mock_exists.return_value = True
        r = client.post("/media/confirm", json={"media_asset_id": asset_id}, headers=user2_headers)
    assert r.status_code == 403
```

- [ ] **Step 2: Run to confirm tests fail (router doesn't exist yet)**

```bash
cd /Users/big_meech/gigs/calendo && source venv/bin/activate && python -m pytest tests/test_media.py -v 2>&1 | head -40
```

Expected: errors importing or 404/500 responses — tests should fail.

- [ ] **Step 3: Commit failing tests**

```bash
git add tests/test_media.py
git commit -m "test: add failing tests for media presign and confirm endpoints"
```

---

### Task 7: Implement media router and wire to main

**Files:**
- Create: `src/backend/routers/media.py`
- Modify: `src/backend/main.py`

- [ ] **Step 1: Create `src/backend/routers/media.py`**

```python
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.backend.database import get_db
from src.backend import models, schemas
from src.backend.auth import get_current_user
from src.backend.r2 import generate_presigned_put, object_exists, EXPIRES_IN
from src.backend.config import R2_PUBLIC_BASE_URL

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MIME_EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
MAX_BYTES = 8 * 1024 * 1024

router = APIRouter(prefix="/media", tags=["media"])


@router.post("/presign", response_model=schemas.PresignResponse)
def presign_upload(
    req: schemas.PresignRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if req.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=422, detail="Unsupported file type")
    if req.size_bytes > MAX_BYTES:
        raise HTTPException(status_code=422, detail="File too large (max 8 MB)")

    ext = MIME_EXT[req.content_type]
    key = f"users/{current_user.id}/media/{uuid.uuid4()}.{ext}"
    public_url = f"{R2_PUBLIC_BASE_URL}/{key}"

    asset = models.MediaAsset(
        user_id=current_user.id,
        storage_key=key,
        public_url=public_url,
        original_filename=req.filename,
        mime_type=req.content_type,
        file_size_bytes=req.size_bytes,
        status="uploaded",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    upload_url = generate_presigned_put(key, req.content_type)

    return schemas.PresignResponse(
        upload_url=upload_url,
        media_asset_id=asset.id,
        storage_key=key,
        public_url=public_url,
        expires_in=EXPIRES_IN,
    )


@router.post("/confirm", response_model=schemas.MediaAssetResponse)
def confirm_upload(
    req: schemas.ConfirmRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    asset = db.query(models.MediaAsset).filter(models.MediaAsset.id == req.media_asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found")
    if asset.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if not object_exists(asset.storage_key):
        raise HTTPException(status_code=422, detail="Object not found in storage")

    asset.status = "ready"
    db.commit()
    db.refresh(asset)
    return asset
```

- [ ] **Step 2: Wire media router into main.py**

Open `src/backend/main.py`. After the existing router imports, add:

```python
from src.backend.routers import media as media_router
```

After `app.include_router(ai_router.router)`, add:

```python
app.include_router(media_router.router)
```

- [ ] **Step 3: Run media tests — all should pass**

```bash
cd /Users/big_meech/gigs/calendo && source venv/bin/activate && python -m pytest tests/test_media.py -v
```

Expected:
```
tests/test_media.py::test_presign_happy_path PASSED
tests/test_media.py::test_presign_invalid_mime PASSED
tests/test_media.py::test_presign_file_too_large PASSED
tests/test_media.py::test_presign_unauthenticated PASSED
tests/test_media.py::test_confirm_happy_path PASSED
tests/test_media.py::test_confirm_object_not_in_r2 PASSED
tests/test_media.py::test_confirm_asset_not_found PASSED
tests/test_media.py::test_confirm_wrong_user PASSED
8 passed
```

- [ ] **Step 4: Run the full test suite to check for regressions**

```bash
cd /Users/big_meech/gigs/calendo && source venv/bin/activate && python -m pytest tests/ -v
```

Expected: all tests pass (no regressions in auth or posts tests).

- [ ] **Step 5: Commit**

```bash
git add src/backend/routers/media.py src/backend/main.py
git commit -m "feat: add /media/presign and /media/confirm endpoints"
```

---

### Task 8: Frontend media service

**Files:**
- Create: `src/frontend/services/media.ts`

- [ ] **Step 1: Create `src/frontend/services/media.ts`**

```typescript
const API_BASE = "/api"

function getHeaders(): HeadersInit {
  const token = localStorage.getItem("token")
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

async function handleResponse(res: Response) {
  if (res.status === 401) {
    localStorage.removeItem("token")
    localStorage.removeItem("email")
    window.location.href = "/login"
    throw new Error("Unauthorized")
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "An error occurred" }))
    throw new Error(err.detail || "Request failed")
  }
  return res.json()
}

export interface PresignRequest {
  filename: string
  content_type: string
  size_bytes: number
}

export interface PresignResponse {
  upload_url: string
  media_asset_id: number
  storage_key: string
  public_url: string
  expires_in: number
}

export async function presign(data: PresignRequest): Promise<PresignResponse> {
  const res = await fetch(`${API_BASE}/media/presign`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(data),
  })
  return handleResponse(res)
}

export async function confirmUpload(data: { media_asset_id: number }): Promise<void> {
  const res = await fetch(`${API_BASE}/media/confirm`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(data),
  })
  return handleResponse(res)
}
```

- [ ] **Step 2: Commit**

```bash
git add src/frontend/services/media.ts
git commit -m "feat: add frontend media service (presign + confirm)"
```

---

### Task 9: MediaUploader component

**Files:**
- Create: `src/frontend/components/MediaUploader.tsx`

- [ ] **Step 1: Create `src/frontend/components/MediaUploader.tsx`**

```tsx
"use client"
import * as React from "react"
import { X, ImageIcon } from "lucide-react"
import { presign, confirmUpload } from "@/services/media"

export interface UploadedMedia {
  mediaAssetId: number
  publicUrl: string
}

interface MediaUploaderProps {
  value?: UploadedMedia | null
  onChange: (media: UploadedMedia | null) => void
  disabled?: boolean
}

export function MediaUploader({ value, onChange, disabled }: MediaUploaderProps) {
  const [uploading, setUploading] = React.useState(false)
  const [progress, setProgress] = React.useState(0)
  const [error, setError] = React.useState<string | null>(null)
  const inputRef = React.useRef<HTMLInputElement>(null)

  const handleFile = async (file: File) => {
    setError(null)
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setError("Only JPEG, PNG, and WebP images are allowed")
      return
    }
    if (file.size > 8 * 1024 * 1024) {
      setError("File must be under 8 MB")
      return
    }

    setUploading(true)
    setProgress(0)
    try {
      const { upload_url, media_asset_id, public_url } = await presign({
        filename: file.name,
        content_type: file.type,
        size_bytes: file.size,
      })

      await new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest()
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) setProgress(Math.round((e.loaded / e.total) * 100))
        }
        xhr.onload = () => (xhr.status === 200 ? resolve() : reject(new Error("Upload to storage failed")))
        xhr.onerror = () => reject(new Error("Upload to storage failed"))
        xhr.open("PUT", upload_url)
        xhr.setRequestHeader("Content-Type", file.type)
        xhr.send(file)
      })

      await confirmUpload({ media_asset_id })
      onChange({ mediaAssetId: media_asset_id, publicUrl: public_url })
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed")
    } finally {
      setUploading(false)
      setProgress(0)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    if (disabled || uploading) return
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
    e.target.value = ""
  }

  if (value) {
    return (
      <div className="relative rounded-md overflow-hidden border border-[#2A2A2A]" style={{ width: 80, height: 80 }}>
        <img src={value.publicUrl} alt="Attached media" className="w-full h-full object-cover" />
        {!disabled && (
          <button
            type="button"
            onClick={() => onChange(null)}
            className="absolute top-1 right-1 rounded-full p-0.5 hover:opacity-80"
            style={{ backgroundColor: "#E1306C" }}
            aria-label="Remove image"
          >
            <X className="w-3 h-3 text-white" />
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-1">
      <div
        role="button"
        tabIndex={disabled ? -1 : 0}
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        onClick={() => !disabled && !uploading && inputRef.current?.click()}
        onKeyDown={(e) => e.key === "Enter" && !disabled && !uploading && inputRef.current?.click()}
        className="flex flex-col items-center justify-center gap-2 rounded-md border border-dashed"
        style={{
          borderColor: "#2A2A2A",
          backgroundColor: "#0F0F0F",
          height: 80,
          opacity: disabled ? 0.5 : 1,
          cursor: disabled ? "not-allowed" : "pointer",
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="sr-only"
          onChange={handleInputChange}
          disabled={disabled}
        />
        {uploading ? (
          <div className="flex flex-col items-center gap-1 w-full px-4">
            <span className="text-xs" style={{ color: "#888888" }}>Uploading… {progress}%</span>
            <div className="w-full rounded-full h-1" style={{ backgroundColor: "#2A2A2A" }}>
              <div
                className="h-1 rounded-full transition-all"
                style={{ width: `${progress}%`, backgroundColor: "#E1306C" }}
              />
            </div>
          </div>
        ) : (
          <>
            <ImageIcon className="w-5 h-5" style={{ color: "#888888" }} />
            <span className="text-xs" style={{ color: "#888888" }}>Drag & drop or click to upload</span>
            <span className="text-xs" style={{ color: "#555555" }}>JPEG · PNG · WebP · max 8 MB</span>
          </>
        )}
      </div>
      {error && <p className="text-xs" style={{ color: "#E1306C" }}>{error}</p>}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/frontend/components/MediaUploader.tsx
git commit -m "feat: add MediaUploader component with drag-drop and XHR progress"
```

---

### Task 10: Update PostModal

**Files:**
- Modify: `src/frontend/components/PostModal.tsx`

- [ ] **Step 1: Update PostData interface in PostModal.tsx**

Open `src/frontend/components/PostModal.tsx`. Find the `PostData` interface and add two optional fields:

```typescript
export interface PostData {
  id?: string
  title: string
  caption: string
  platform: Platform
  platforms?: Platform[]
  scheduledDate: Date
  status: PostStatus
  scheduledTime?: string
  notes?: string
  mediaAssetId?: number
  mediaPublicUrl?: string
}
```

- [ ] **Step 2: Add MediaUploader import at the top of PostModal.tsx**

After the existing import for `AICaptionButton`, add:

```typescript
import { MediaUploader, type UploadedMedia } from "@/components/MediaUploader"
```

- [ ] **Step 3: Add media state in the PostModal component function**

In `PostModal`, after the `const [calendarOpen, setCalendarOpen]` line, add:

```typescript
  const [media, setMedia] = React.useState<UploadedMedia | null>(null)
```

- [ ] **Step 4: Initialise media state in useEffect**

In the `useEffect` block, inside the `if (post)` branch, after `setNotes(post.notes || "")`, add:

```typescript
        setMedia(post.mediaAssetId && post.mediaPublicUrl
          ? { mediaAssetId: post.mediaAssetId, publicUrl: post.mediaPublicUrl }
          : null)
```

In the `else` branch, after `setNotes("")`, add:

```typescript
        setMedia(null)
```

- [ ] **Step 5: Pass media fields in handleSave**

In `handleSave`, the two `onSave(...)` calls each need `mediaAssetId` and `mediaPublicUrl`. Update both:

For the `mode === "create"` branch, change `onSave({...})` to:

```typescript
      onSave({
        id: post?.id,
        title: title.trim(),
        caption: caption.trim(),
        platform: selectedPlatforms[0],
        platforms: selectedPlatforms,
        scheduledDate: date,
        status,
        scheduledTime: scheduledTime || undefined,
        notes: notes.trim() || undefined,
        mediaAssetId: media?.mediaAssetId,
        mediaPublicUrl: media?.publicUrl,
      })
```

For the `else` (edit) branch, change `onSave({...})` to:

```typescript
      onSave({
        id: post?.id,
        title: title.trim(),
        caption: caption.trim(),
        platform,
        scheduledDate: date,
        status,
        scheduledTime: scheduledTime || undefined,
        notes: notes.trim() || undefined,
        mediaAssetId: media?.mediaAssetId,
        mediaPublicUrl: media?.publicUrl,
      })
```

- [ ] **Step 6: Add Media section to the form JSX**

In the `PostModal` JSX, find the `<div className="flex flex-col gap-2">` block containing the Internal Notes textarea (it's the last field before the `</div>` that closes the scrollable area). Add a new media section **before** the Notes block:

```tsx
          <div className="flex flex-col gap-2">
            <Label style={{ color: "#F5F5F5" }}>Media</Label>
            <MediaUploader
              value={media}
              onChange={setMedia}
              disabled={isPublished}
            />
          </div>
```

- [ ] **Step 7: Verify TypeScript compiles**

```bash
cd /Users/big_meech/gigs/calendo/src/frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected: no errors.

- [ ] **Step 8: Commit**

```bash
git add src/frontend/components/PostModal.tsx
git commit -m "feat: add media upload section to PostModal"
```

---

### Task 11: Update CalendarGrid to show thumbnails

**Files:**
- Modify: `src/frontend/components/CalendarGrid.tsx`

- [ ] **Step 1: Add mediaPublicUrl to the Post interface**

In `src/frontend/components/CalendarGrid.tsx`, find the `Post` interface and add:

```typescript
export interface Post {
  id: string
  title: string
  platform: Platform
  date: Date
  status?: PostStatus
  scheduledTime?: string
  mediaPublicUrl?: string
}
```

- [ ] **Step 2: Show thumbnail in PostChip**

Find the `PostChip` component. After the `<span className="truncate">` that shows title/time, add a thumbnail if `post.mediaPublicUrl` exists. Update the entire `PostChip` render return:

```tsx
  return (
    <div
      onClick={(e) => { e.stopPropagation(); onClick(post) }}
      className={cn(
        "flex w-full items-center gap-1 truncate rounded-full px-2 py-0.5 text-left text-xs font-medium text-white transition-opacity hover:opacity-80 cursor-pointer",
        status === "draft" && "bg-transparent"
      )}
      style={getChipStyles()}
      title={`${post.title} (${post.platform}) - ${status}`}
    >
      {status === "published" && <Check className="h-3 w-3 shrink-0" />}
      {post.mediaPublicUrl && (
        <img
          src={post.mediaPublicUrl}
          alt=""
          className="h-3.5 w-3.5 rounded-sm object-cover shrink-0"
        />
      )}
      <span className="truncate">
        {post.title}{post.scheduledTime ? ` · ${formatTime12h(post.scheduledTime)}` : ""}
      </span>
    </div>
  )
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd /Users/big_meech/gigs/calendo/src/frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add src/frontend/components/CalendarGrid.tsx
git commit -m "feat: show media thumbnail in calendar post chip"
```

---

### Task 12: Thread media fields through dashboard page

**Files:**
- Modify: `src/frontend/app/dashboard/page.tsx`

- [ ] **Step 1: Update ApiPost interface to include media fields**

In `src/frontend/app/dashboard/page.tsx`, find the `ApiPost` interface and add:

```typescript
interface ApiPost {
  id: number
  title: string
  caption: string | null
  platform: string
  scheduled_date: string
  status: string
  scheduled_time: string | null
  notes: string | null
  media_asset_id: number | null
  media_public_url: string | null
}
```

- [ ] **Step 2: Update toCalendarPost to pass mediaPublicUrl**

Find `function toCalendarPost(p: ApiPost): CalendarPost` and update it:

```typescript
function toCalendarPost(p: ApiPost): CalendarPost {
  return {
    id: String(p.id),
    title: p.title,
    platform: p.platform as Platform,
    date: new Date(p.scheduled_date + "T00:00:00"),
    status: p.status as PostStatus,
    scheduledTime: p.scheduled_time || undefined,
    mediaPublicUrl: p.media_public_url || undefined,
    _raw: p,
  }
}
```

- [ ] **Step 3: Update handlePostClick to pass media fields to PostData**

Find `handlePostClick`. Update the `setSelectedPost(...)` call to include media fields:

```typescript
    setSelectedPost({
      id: String(raw.id),
      title: raw.title,
      caption: raw.caption || "",
      platform: raw.platform as Platform,
      scheduledDate: new Date(raw.scheduled_date + "T00:00:00"),
      status: raw.status as PostStatus,
      scheduledTime: raw.scheduled_time || undefined,
      notes: raw.notes || undefined,
      mediaAssetId: raw.media_asset_id || undefined,
      mediaPublicUrl: raw.media_public_url || undefined,
    })
```

- [ ] **Step 4: Update handleSave to pass media_asset_id in API calls**

Find `handleSave`. Update `baseBody` to include `media_asset_id`:

```typescript
    const baseBody = {
      title: postData.title,
      caption: postData.caption,
      scheduled_date: toLocalDateString(postData.scheduledDate),
      status: postData.status,
      scheduled_time: postData.scheduledTime || null,
      notes: postData.notes || null,
      media_asset_id: postData.mediaAssetId || null,
    }
```

- [ ] **Step 5: Update tempRaw objects to include media fields**

There are two `tempRaw` objects in `handleSave` (one for create, one for edit). Both need the media fields. Update both:

For the create branch `tempRaw`:
```typescript
      const tempRaw: ApiPost = {
        id: 0,
        title: postData.title,
        caption: postData.caption || null,
        platform: postData.platform,
        scheduled_date: toLocalDateString(postData.scheduledDate),
        status: postData.status,
        scheduled_time: postData.scheduledTime || null,
        notes: postData.notes || null,
        media_asset_id: postData.mediaAssetId || null,
        media_public_url: postData.mediaPublicUrl || null,
      }
```

For the edit branch `tempRaw`:
```typescript
      const tempRaw: ApiPost = {
        id: parseInt(postData.id),
        title: postData.title,
        caption: postData.caption || null,
        platform: postData.platform,
        scheduled_date: toLocalDateString(postData.scheduledDate),
        status: postData.status,
        scheduled_time: postData.scheduledTime || null,
        notes: postData.notes || null,
        media_asset_id: postData.mediaAssetId || null,
        media_public_url: postData.mediaPublicUrl || null,
      }
```

- [ ] **Step 6: Verify TypeScript compiles**

```bash
cd /Users/big_meech/gigs/calendo/src/frontend && npx tsc --noEmit 2>&1 | head -30
```

Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add src/frontend/app/dashboard/page.tsx
git commit -m "feat: thread media_asset_id and media_public_url through dashboard"
```

---

### Task 13: Full test run and final commit

**Files:** none — verification only

- [ ] **Step 1: Run all backend tests**

```bash
cd /Users/big_meech/gigs/calendo && source venv/bin/activate && python -m pytest tests/ -v
```

Expected: all tests pass. If any fail, fix before proceeding.

- [ ] **Step 2: Build frontend to check for type errors**

```bash
cd /Users/big_meech/gigs/calendo/src/frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Final summary commit**

```bash
git add -A
git commit -m "feat: Phase 2 media library on R2 — complete implementation"
```

---

## Migration command (for production)

```bash
alembic upgrade head
```

## R2 bucket CORS policy

Set this on your R2 bucket (Cloudflare dashboard → R2 → Bucket → Settings → CORS):

```json
[
  {
    "AllowedOrigins": ["https://<your-vercel-domain>.vercel.app", "http://localhost:3000"],
    "AllowedMethods": ["PUT"],
    "AllowedHeaders": ["*"],
    "MaxAgeSeconds": 3600
  }
]
```

Replace `<your-vercel-domain>` with your actual Vercel domain.

## Local test commands

```bash
# Presign (replace TOKEN with a real JWT)
curl -X POST http://localhost:8000/media/presign \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"filename":"test.jpg","content_type":"image/jpeg","size_bytes":10240}'

# Confirm (replace ASSET_ID with the id from presign)
curl -X POST http://localhost:8000/media/confirm \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"media_asset_id": ASSET_ID}'
```

## New env vars

| Variable | Where to set |
|----------|-------------|
| `R2_ACCOUNT_ID` | Render dashboard + local `.env` |
| `R2_ACCESS_KEY_ID` | Render dashboard + local `.env` |
| `R2_SECRET_ACCESS_KEY` | Render dashboard + local `.env` |
| `R2_BUCKET` | Render dashboard + local `.env` |
| `R2_PUBLIC_BASE_URL` | Render dashboard + local `.env` |
