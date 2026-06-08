# Design: Phase 2 — Media Library on R2

Source spec: `CALENDO_AI_MEDIA_SPEC.md`

## Architecture

Presigned-upload pattern — FastAPI never holds file bytes. Flow:
1. Client calls `POST /media/presign` → gets a presigned R2 PUT URL + `media_asset_id`
2. Client PUTs file directly to R2 (progress via XHR)
3. Client calls `POST /media/confirm` → server verifies object exists, sets status `ready`
4. Client saves post with `media_asset_id` attached

## Schema (migration 005)

**New table `media_asset`**
- `id` INTEGER PK
- `user_id` INTEGER FK → users.id NOT NULL
- `storage_key` TEXT NOT NULL
- `provider` TEXT DEFAULT 'r2'
- `public_url` TEXT
- `original_filename` TEXT
- `mime_type` TEXT
- `file_size_bytes` BIGINT
- `width` INTEGER nullable
- `height` INTEGER nullable
- `status` TEXT DEFAULT 'uploaded' (uploaded / processing / ready / failed)
- `created_at` TIMESTAMPTZ

**Alter `posts`**
- Add `media_asset_id` INTEGER nullable FK → media_asset.id

## Backend

### New files
- `src/backend/r2.py` — boto3 client factory, `generate_presigned_put`, `object_exists`
- `src/backend/routers/media.py` — `/media/presign` and `/media/confirm`

### Modified files
- `src/backend/config.py` — add R2_* env vars
- `src/backend/models.py` — MediaAsset model, media_asset_id on Post
- `src/backend/schemas.py` — PresignRequest/Response, ConfirmRequest, MediaAssetResponse; add media_asset_id to PostCreate/PostUpdate/PostResponse
- `src/backend/main.py` — include media router
- `requirements.txt` — add boto3, aioboto3
- `alembic/versions/005_add_media_assets.py` — migration

### Validation
- Allowed mime types: `image/jpeg`, `image/png`, `image/webp`
- Max size: 8,388,608 bytes (8 MB)
- Storage key pattern: `users/{user_id}/media/{uuid}.{ext}`

## Frontend

### New files
- `src/frontend/components/MediaUploader.tsx` — drag/drop zone, XHR upload with progress
- `src/frontend/services/media.ts` — `presign()`, `confirm()`

### Modified files
- `src/frontend/components/PostModal.tsx` — media upload section; PostData gets `mediaAssetId?`, `mediaPublicUrl?`
- `src/frontend/components/CalendarGrid.tsx` — Post interface gets `mediaPublicUrl?`; PostChip shows thumbnail square
- `src/frontend/services/posts.ts` — pass `media_asset_id` in create/update payloads

## Tests

`tests/test_media.py` — mock boto3 via `unittest.mock.patch`:
- presign: happy path, invalid mime, file too large, unauthenticated
- confirm: happy path, wrong user, asset not found, object not in R2

## Env vars

| Var | Where |
|-----|-------|
| R2_ACCOUNT_ID | Render env + .env |
| R2_ACCESS_KEY_ID | Render env + .env |
| R2_SECRET_ACCESS_KEY | Render env + .env |
| R2_BUCKET | Render env + .env |
| R2_PUBLIC_BASE_URL | Render env + .env |

## R2 CORS policy

```json
[{
  "AllowedOrigins": ["https://<vercel-domain>", "http://localhost:3000"],
  "AllowedMethods": ["PUT"],
  "AllowedHeaders": ["*"],
  "MaxAgeSeconds": 3600
}]
```
