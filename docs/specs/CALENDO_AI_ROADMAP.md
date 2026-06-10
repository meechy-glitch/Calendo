# Calendo AI — Build Roadmap (v1 hand-off / v2 direct publish)

Reworked around shipping fast. **v1 = assisted "hand-off" posting on all four platforms**
(no platform APIs, no approvals, no fees) — a complete, demoable product you can build now.
**v2 = true auto-publish as a premium upgrade**, added per platform as approvals land.
Build all of v1 immediately; start the v2 approval clocks in parallel on day one.

---

## The core decision
v1 does NOT call platform APIs. At a post's scheduled time, Calendo notifies the user and
hands them a ready-to-post payload — caption to copy, media to download, and a deep-link /
intent where the platform supports it. The user taps post and marks it done. Ships now,
free, on all four platforms. Direct API publishing becomes the v2 paid tier.

---

## v1 — Ship now (no external approvals, no API costs)

### Phase 1 — The AI brain
Spec: `CALENDO_AI_SPEC.md`. Caption assistant, platform rewrite, brand-voice memory,
conversational (tool-use) assistant. No external dependencies — build first.

### Phase 2 — Media library on R2
Presigned client->R2 upload, `media_asset` table, attach media to posts, calendar
thumbnails. Needed so media can be stored, previewed, and downloaded for hand-off.
(From the media half of the old publish spec.)

### Phase 3 — Image-aware captioning
Spec: `CALENDO_AI_VISION_SPEC.md`. Uploaded image -> Claude vision -> caption + suggested
platform.

### Phase 4 — Video upload + thumbnails
Presigned video upload to R2, ffmpeg thumbnail, the `post_media` junction (multi-media +
ordering), per-platform spec validation/warnings. (Media half of the video spec — NOT the
publishing half.)

### Phase 5 — Hand-off / publish-assist engine   <-- THE NEW CORE OF v1
- Reminder cron (external cron -> `/internal/notify-due`) finds posts due at `scheduled_at`
  (UTC) and notifies the user via the existing Resend email + in-app.
- "Post now" hand-off view per post:
  - caption with a copy button, media download,
  - X: intent URL (pre-fills text),
  - LinkedIn: share URL,
  - Instagram / TikTok: no intent -> open-app deep link + copy caption + download media.
- Status flow: scheduled -> ready (notified) -> posted (the user taps "Mark as posted",
  since Calendo can't verify publication without the API).
- Per-platform spec validation/warnings before scheduling.

### Phase 6 — Voice input
Spec: `CALENDO_AI_VOICE_SPEC.md`. Mic button on the chat assistant panel and the caption
idea field. Part A: Browser Web Speech API (frontend only, no backend). Part B: Groq
Whisper transcription endpoint (broader browser support + higher accuracy).

That's a complete shippable product: plan -> AI-assisted content -> media ready ->
reminder -> post in a couple taps.

---

## v2 — Direct auto-publish (premium; add per platform as approvals land)

Start these approval clocks on DAY ONE so they're ready when you reach this stage.

### Phase 6 — Social accounts + OAuth + token security
`social_accounts` table, AES-256-GCM encrypted tokens, OAuth flows, refresh-before-call
with the X refresh mutex. (From the old publish spec.)

### Phase 7 — Direct publishing engine + X first
Publisher abstraction, cron-publish state machine (`FOR UPDATE SKIP LOCKED`), X direct
posting. NOTE: X is pay-per-use (~$0.015/post, ~$0.20 per post containing a URL).

### Phase 8 — LinkedIn direct  (approved ~1-3 days)
### Phase 9 — Instagram direct  (after Meta App Review, 2-6 weeks + likely a resubmit)
### Phase 10 — TikTok direct  (after audit; draft-only until then)

Direct publish is the paid upgrade: "Calendo posts for you, automatically."

---

## Day-1 parallel actions (start the v2 clocks now)
- **X** developer access — instant; pay-per-use, load a small credit balance.
- **LinkedIn** — app + verified Company Page + "Share on LinkedIn" product (~1-3 days).
- **Instagram** — Meta app (Business) + Instagram Graph API + App Review (2-6 wks). THE LONG POLE.
- **TikTok** — TikTok for Developers app + Content Posting API + start the audit.
- **Cloudflare R2** — bucket + CORS (PUT from Vercel origin + localhost). Needed for v1 too.

---

## Spec file mapping
- `CALENDO_AI_SPEC.md` -> Phase 1 (v1) — the AI brain.
- `CALENDO_AI_MEDIA_SPEC.md` -> Phase 2 (v1) — media library on R2.
- `CALENDO_AI_VISION_SPEC.md` -> Phase 3 (v1) — image-aware captioning.
- `CALENDO_AI_VIDEO_SPEC.md` -> Phase 4 (v1) — video upload + thumbnails (NO publishing).
- `CALENDO_AI_HANDOFF_SPEC.md` -> Phase 5 (v1) — hand-off / publish-assist engine.
- `CALENDO_AI_VOICE_SPEC.md` -> Phase 6 (v1) — voice input.
- `CALENDO_AI_PUBLISH_SPEC.md` -> Phases 7-8 (v2) — OAuth + direct publishing (premium).

---

## Stack
FastAPI on Render · Supabase Postgres · Cloudflare R2 (media, zero egress) · external cron ·
Claude Sonnet 4.6 · ffmpeg (thumbnails only) · Resend (notifications) · Alembic.

## Landmines — all in v2; v1 sidesteps them entirely
- X charges ~$0.20 per post containing a URL (pay-per-use).
- X refresh tokens rotate — concurrent refresh locks the user out; use a mutex.
- Instagram fetches media FROM your URL, JPEG-only images, 25 publish calls/hour, slow App Review.
- TikTok is draft-only until your app passes audit.

## What v1 trades away (the honest cost)
v1 can't confirm a post actually went out (the user marks it posted), and it isn't fully
automatic. That's the deliberate trade for shipping now, on all four platforms, with zero
approvals and zero API cost. v2 restores full automation as the premium tier.
