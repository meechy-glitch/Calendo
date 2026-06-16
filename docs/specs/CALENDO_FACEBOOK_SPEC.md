# Calendo — Add Facebook as a platform

Add Facebook as a fifth platform alongside Instagram, X, TikTok, LinkedIn. KEEP LinkedIn — this is an addition, not a replacement. Frontend + small config now (v1 hand-off); the direct-publish piece is deferred to v2 and bundled with the Instagram/Meta publisher because Facebook shares Meta's Graph API.

## Conventions
- Python `str | None`, Python 3.11. Alembic for any schema change. Reuse existing patterns.
- Frontend uses /api/* rewrite. Existing platform colors: Instagram #833AB4, X #888888, TikTok #FE2C55, LinkedIn #0A66C2.
- Facebook brand color: **#1877F2**.

## Part A — v1 (do now): Facebook as a hand-off platform
- Add `facebook` everywhere the other platforms are enumerated: the platform enum/allowed set (backend validation + the AI tools' platform enums), the frontend platform filter chips, the post form platform selector, calendar chip colors, and analytics breakdown.
- Color: #1877F2. Add it to the platform color map (dot, chip, label) on both frontend and any backend reference.
- Hand-off action (Phase 5 hand-off engine): Facebook has no reliable pre-filled compose intent for Pages, so treat it like Instagram/TikTok — provide the caption (copy button), media (download), and an "Open Facebook" deep link / link to the user's Page. Add a facebook case to the GET /posts/{id}/handoff platform-action logic.
- Per-platform spec validation (video spec): add a Facebook entry (MP4, generous size — verify current limits) so video warnings cover it. Warnings only, no publishing.
- Update the AI assistant's platform-aware caption/rewrite guidance to include a Facebook style (conversational, slightly longer than X, link-friendly, 1-2 hashtags max).

## Part B — v2 (note for later, do NOT build now): Facebook direct publishing
- Facebook Page publishing uses the Meta Graph API — the SAME app, OAuth, and App Review as Instagram. Implement it in the SAME v2 phase as the Instagram publisher, not separately.
- Scopes to add to the Meta app: pages_manage_posts, pages_read_engagement, pages_show_list.

## Constraints
- Do NOT remove LinkedIn.
- Part A only for now (frontend + config + hand-off). No OAuth, no publishing, no Meta work.
- No feature regressions.

## Delivery
- platform/status are VARCHAR already, so likely no migration needed — confirm.
- Test: create a Facebook post, see it on the calendar with the #1877F2 color, filter by Facebook, and open its hand-off view. Confirm the AI assistant accepts 'facebook' as a platform in caption/create requests.
- Do not commit — show me test results first.
