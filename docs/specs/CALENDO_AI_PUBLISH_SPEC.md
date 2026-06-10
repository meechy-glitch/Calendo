# Calendo AI — Phases 6-7 (v2, PREMIUM): OAuth + direct auto-publish (X first)

The premium upgrade on top of v1. v1 already ships hand-off posting; this phase adds TRUE
auto-publish — Calendo posts on the user's behalf via the platform API. Builds on all of
v1 (the media library, scheduled_at, and post_media already exist). Same conventions.

First platform implemented end-to-end: **X**. NOTE: X is PAY-PER-USE (Feb 2026) —
~$0.015/standard post and ~$0.20 per post that contains a URL; the old free tier is gone
for new signups. LinkedIn / Instagram / TikTok direct publishing are later v2 phases,
stubbed behind the same interface.

## Hard conventions
- Python `str | None`, Python 3.11. Alembic for ALL schema changes (no hand edits).
- Reuse get_current_user, slowapi limiter. Frontend uses /api/* rewrite.
- Secrets via env ONLY: ENCRYPTION_KEY, INTERNAL_CRON_SECRET (exists), X_CLIENT_ID,
  X_CLIENT_SECRET, X_REDIRECT_URI. Never hardcode.
- Design tokens: bg #0F0F0F, surface #1A1A1A, accent #E1306C, text #F5F5F5,
  muted #888888, border #2A2A2A. Platform colors: IG #833AB4, X #888888,
  TikTok #FE2C55, LinkedIn #0A66C2.

## Schema (additions on top of v1)
- posts: add social_account_id FK (nullable), platform_post_id TEXT, published_url TEXT,
  published_at TIMESTAMPTZ, error_message TEXT, retry_count INT DEFAULT 0, and a
  publish_mode TEXT DEFAULT 'handoff' ('handoff' = v1 path, 'auto' = this premium path).
  Extend status to also support: publishing, published, failed, failed_permanent.
- post_media: add platform_media_id TEXT null, upload_status TEXT DEFAULT 'pending'
  (pending/uploading/ready/failed).
- MATCH EXISTING PK TYPES. Alembic migrations + exact upgrade command.

## Component A — Social accounts + token security
- Table `social_accounts`: id, user_id FK ON DELETE CASCADE, platform TEXT
  (x/linkedin/instagram/tiktok), platform_user_id TEXT, platform_username TEXT,
  access_token TEXT (ENCRYPTED), refresh_token TEXT (ENCRYPTED, nullable),
  token_expires_at TIMESTAMPTZ, scopes TEXT[], status TEXT DEFAULT 'active'
  (active/expired/revoked), connected_at TIMESTAMPTZ, last_refreshed_at TIMESTAMPTZ,
  UNIQUE(user_id, platform).
- ENCRYPTION: AES-256-GCM (cryptography library's AESGCM), key from ENCRYPTION_KEY env.
  Decrypt ONLY at the moment of an API call. Never log decrypted tokens.
- X OAuth 2.0 with PKCE: connect + callback endpoints. Scopes: tweet.read, tweet.write,
  users.read, offline.access, media.upload. Random `state` for CSRF. Store tokens encrypted.
- Stub LinkedIn/Instagram/TikTok connect endpoints (later v2 phases).

### Token refresh — with a MUTEX (critical for X)
- Before any platform call, if token_expires_at is within 5 minutes, refresh first.
- X refresh tokens ROTATE on every use; a concurrent double-refresh PERMANENTLY locks the
  user out. Wrap refresh in a transaction that does `SELECT ... FOR UPDATE` on the
  social_accounts row (serializing per account), RE-CHECK expiry inside the lock, refresh,
  store the NEW rotated refresh_token + access_token, update last_refreshed_at, commit.
- On refresh failure (revoked): set status 'expired' and surface a "reconnect" prompt.

## Component B — Publisher abstraction + X
- `Publisher` interface: async publish(post, social_account, media_url: str | None)
  -> result(platform_post_id, published_url).
- Implement X for TEXT + IMAGE posts (video is a later v2 phase): refresh token first (with
  the mutex), upload image media, attach the media id, create the tweet. Validate per-X
  limits (image 5MB, JPEG/PNG/GIF). Capture id + URL.
- Stub LinkedIn/Instagram/TikTok publish methods (NotImplemented + TODO).

## Component C — Publish cron (separate from v1's notify cron)
- `POST /internal/publish-due`, protected by INTERNAL_CRON_SECRET. NOT behind user JWT.
- Claim due posts where publish_mode='auto' AND status='scheduled' AND scheduled_at <=
  now() (UTC) with `SELECT ... FOR UPDATE SKIP LOCKED`; set status 'publishing'.
  (Posts with publish_mode='handoff' stay on the v1 notify path — do not touch them.)
- Resolve social_account + media public_url, call the Publisher.
- Success -> status 'published', store platform_post_id, published_url, published_at.
- Failure -> increment retry_count. If < 3, status back to 'scheduled' with scheduled_at =
  now() + backoff (retry 1: +2 min, 2: +10 min, 3: +1 hr) + error_message. If >= 3 ->
  'failed_permanent'. Expose `POST /posts/{id}/retry`.

## Frontend
- "Connect X" button + status (active / needs reconnect).
- On the post form, a toggle for auto-publish (sets publish_mode='auto'); requires a
  connected account, else fall back to hand-off. Show publish status + errors + Retry in
  the calendar. Theme with the tokens.

## Out of scope (later v2 phases)
- Video publishing, LinkedIn / Instagram / TikTok direct publishing.

## Delivery
- Alembic migrations + exact upgrade command. Add boto3/aioboto3 (if not present) and
  cryptography to requirements.txt.
- Every new env var + where to set it (Render + local .env), the X developer app setup
  (redirect URI, scopes), and the external cron setup for /internal/publish-due.
- Local test commands (OAuth connect + a /internal/publish-due dry run) and the git
  add/commit/push commands. Remind me to set all env vars in Render before pushing.
