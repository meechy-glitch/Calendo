# Calendo AI — Phase 2 (v1): Media library on R2

Builds on Phase 1. Existing FastAPI + Next.js 14 app, Supabase Postgres, media on
**Cloudflare R2** (S3-compatible, zero egress). No platform APIs in this phase. Follow ALL
existing conventions.

## Hard conventions
- Python `str | None`, Python 3.11. Alembic for ALL schema changes (no hand edits).
- Reuse get_current_user and the slowapi limiter. Frontend uses the existing /api/* rewrite.
- Secrets via env ONLY: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET,
  R2_PUBLIC_BASE_URL. Never hardcode.
- Design tokens: bg #0F0F0F, surface #1A1A1A, accent #E1306C, text #F5F5F5,
  muted #888888, border #2A2A2A.

## Schema
- Table `media_asset`: id, user_id FK, storage_key TEXT, provider TEXT DEFAULT 'r2',
  public_url TEXT, original_filename TEXT, mime_type TEXT, file_size_bytes BIGINT,
  width INT, height INT, status TEXT DEFAULT 'uploaded' (uploaded/processing/ready/failed),
  created_at TIMESTAMPTZ. (Phase 4 adds duration_seconds + thumbnail_key for video.)
- Add a nullable `media_asset_id` FK on the existing `posts` table (single media for now;
  Phase 4 migrates this into a `post_media` junction).
- MATCH EXISTING PK TYPES for all FKs. Generate Alembic migrations + give me the exact
  `alembic upgrade head` command.

## Presigned direct upload (bytes never touch Render)
- Use an S3-compatible client (boto3/aioboto3) pointed at the R2 endpoint.
- `POST /media/presign`: body { filename, content_type, size_bytes }. Validate type
  (jpeg/png/webp) and size (cap ~8MB for images). Create the media_asset row (status
  'uploaded'), generate a presigned R2 PUT URL for key
  `users/{user_id}/media/{uuid}.{ext}`, return { upload_url, media_asset_id, storage_key,
  public_url, expires_in }.
- `POST /media/confirm`: body { media_asset_id }. Verify the object exists in R2, set
  status 'ready'. The CLIENT uploads bytes straight to R2 — FastAPI never holds the file.
- R2 BUCKET CORS: give me the exact CORS policy allowing PUT from the Vercel frontend
  origin AND http://localhost:3000, or browser uploads will fail.

## Frontend
- Drag/drop uploader (direct-to-R2 with a progress bar) + a media picker on the post form.
- Show attached media as a thumbnail on the post and in the calendar grid. Theme with tokens.

## Delivery
- Alembic migration + exact upgrade command. Add boto3/aioboto3 to requirements.txt.
- Every new env var + where to set it (Render + local .env), and the R2 bucket + CORS steps.
- Local test commands (presign + confirm) and the git add/commit/push commands.
