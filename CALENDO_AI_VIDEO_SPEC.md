# Calendo AI — Phase 4 (v1): Video upload + thumbnails (NO publishing)

Builds on Phase 2 (media library on R2). In v1, video is just an extended media asset —
this phase handles upload, processing, and multi-media attachment. It does NOT publish to
any platform (direct publishing is v2). Same conventions throughout.

## Hard conventions
- Python `str | None`, Python 3.11. Alembic for ALL schema changes (no hand edits).
- Reuse get_current_user, slowapi limiter, the existing /media/presign + /media/confirm
  flow. Frontend uses /api/* rewrite. Secrets via env only (existing R2_*).
- Design tokens: bg #0F0F0F, surface #1A1A1A, accent #E1306C, text #F5F5F5,
  muted #888888, border #2A2A2A. Platform colors: IG #833AB4, X #888888,
  TikTok #FE2C55, LinkedIn #0A66C2.

## Schema
1. EXTEND media_asset: add duration_seconds FLOAT null, thumbnail_key TEXT null.
2. CREATE post_media junction: post_id FK -> posts(id) ON DELETE CASCADE, media_id FK ->
   media_asset(id), position INT default 0, UNIQUE(post_id, position).
   (v2 will add platform_media_id + upload_status for direct publishing — not needed now.)
3. MIGRATE the existing posts.media_asset_id single FK into post_media at position 0 via a
   data migration, then DROP posts.media_asset_id.
4. MATCH EXISTING PK TYPES. Generate Alembic migrations + the exact upgrade command.

## Video upload (extends the Phase 2 presigned flow)
- Extend /media/presign + /media/confirm validation to accept video (mp4/mov) with a higher
  cap (e.g. 50MB).
- On confirm for a video: set status 'processing', run ffmpeg to (a) probe
  duration/width/height, (b) extract a thumbnail frame (~1s in), upload the thumb to R2 as
  thumbnail_key, then set status 'ready'. Inline but capped for now.
- Add ffmpeg to the Docker image: `apt-get install -y ffmpeg` alongside libpq-dev/gcc.

## Per-platform spec validation (warnings only — no publishing)
- Validation function with a per-platform spec table (size, mime, max duration, aspect):
  X (50MB, MP4), LinkedIn (200MB, MP4, 3s-10min), Instagram (100MB, MP4 H.264/AAC, reels
  9:16 3-90s — verify), TikTok (vertical 9:16, MP4/MOV — verify). Warn the user in the UI
  when a video doesn't meet the target platform's specs. Do NOT auto-reframe.

## Frontend
- Video upload via presigned URL with a progress bar (direct to R2); show 'processing'
  until media_asset status = ready.
- Calendar grid: thumbnail with a small play badge for video posts.
- Post form: attach multiple media with drag-to-reorder (position) + per-platform spec
  warnings. Theme with the tokens.

## Out of scope (v2)
- Any platform publishing / chunked uploads / OAuth — all v2.

## Delivery
- Alembic migrations + exact upgrade command. The Dockerfile ffmpeg change.
- Local test commands (presign/confirm a video) and the git add/commit/push commands.
