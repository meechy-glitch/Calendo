# Calendo AI — Phase 5 (v1): Hand-off / publish-assist engine

The core of v1. At a post's scheduled time, Calendo notifies the user and hands them a
ready-to-post payload (caption to copy, media to download, a deep-link/intent where
supported). The user posts on the platform and marks it done. NO platform APIs, no OAuth,
no approvals. Builds on Phases 1-4. Same conventions.

## Hard conventions
- Python `str | None`, Python 3.11. Alembic for ALL schema changes (no hand edits).
- Reuse get_current_user, slowapi limiter, and the EXISTING Resend email integration (the
  one already used for password reset). Frontend uses /api/* rewrite.
- Secrets via env only: existing RESEND_API_KEY + INTERNAL_CRON_SECRET. Never hardcode.
- Design tokens: bg #0F0F0F, surface #1A1A1A, accent #E1306C, text #F5F5F5,
  muted #888888, border #2A2A2A. Platform colors: IG #833AB4, X #888888,
  TikTok #FE2C55, LinkedIn #0A66C2.

## Schema (additions to the existing posts table)
- `scheduled_at TIMESTAMPTZ` (UTC) — backfill from the existing scheduled_date +
  scheduled_time; this is the source of truth for the reminder cron. Convert from the
  user's timezone at the API layer on create/update.
- Status supports: draft, scheduled, ready, posted, skipped.
- `notified_at TIMESTAMPTZ` (the "ready to post" notification was sent),
  `lead_notified_at TIMESTAMPTZ` (optional 24h-before heads-up sent),
  `posted_at TIMESTAMPTZ`, `posted_url TEXT` (optional, user can paste the live link).
- Partial index: `CREATE INDEX idx_posts_due ON posts(status, scheduled_at)
  WHERE status = 'scheduled';`
- MATCH EXISTING PK TYPES. Alembic migration + exact upgrade command.

## Reminder cron (external cron -> protected endpoint)
- `POST /internal/notify-due`, protected by a header secret == INTERNAL_CRON_SECRET (reject
  otherwise). NOT behind user JWT.
- Logic, using `FOR UPDATE SKIP LOCKED` to avoid double-notify:
  1. "Ready to post": posts where status='scheduled' AND scheduled_at <= now() (UTC) AND
     notified_at IS NULL -> send the user a "ready to post" email (Resend) + set an in-app
     flag, set notified_at = now(), status -> 'ready'.
  2. Optional lead reminder: posts where scheduled_at is ~24h away AND lead_notified_at IS
     NULL AND the user has lead reminders enabled -> send a heads-up, set lead_notified_at.
- Give me the external cron setup (cron-job.org or GitHub Actions) POSTing to
  /internal/notify-due every few minutes with the secret header.

## Hand-off payload
- `GET /posts/{id}/handoff` (user-scoped) returns: caption text, media public_urls +
  download links, platform, and a platform action:
  - **X**: intent URL, e.g. `https://x.com/intent/post?text={urlencoded caption}`
    (pre-fills text; media is added manually after download).
  - **LinkedIn**: a share URL (feed share / share-offsite). Note pre-fill is limited to
    text/links.
  - **Instagram / TikTok**: NO posting intent exists — return an open-app deep link
    (e.g. `instagram://app`, TikTok app link) plus the caption (copy) and media (download).
- `POST /posts/{id}/mark-posted`: body { posted_url?: str | None } -> status 'posted',
  posted_at = now(), store posted_url if provided. (Calendo can't verify publication
  without the API, so the user confirms.)
- `POST /posts/{id}/skip` -> status 'skipped'.

## Frontend
- A "Ready to post" queue (today's + overdue notified posts) on the dashboard.
- Per-post "Post now" modal: caption with a copy button, media preview + download,
  the platform action button (intent/share link for X/LinkedIn; "Open app" + copy/download
  for IG/TikTok), and a "Mark as posted" button (with an optional field to paste the live
  URL). A "Skip" option.
- In-app notification indicator when posts become 'ready'.
- A settings toggle for the optional 24h lead reminder. Theme everything with the tokens.

## Out of scope (v2)
- Any direct API publishing, OAuth, token storage — all v2 (premium auto-publish).

## Delivery
- Alembic migration + exact upgrade command.
- The external cron setup for /internal/notify-due.
- Local test commands (a /internal/notify-due dry run with the secret header + a
  /posts/{id}/handoff fetch) and the git add/commit/push commands. Remind me to set
  INTERNAL_CRON_SECRET in Render before pushing.
