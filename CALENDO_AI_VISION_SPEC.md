# Calendo AI — Phase 3: Image-aware captioning (Groq-first)

Small feature on top of Phase 1 (caption + brand_voice + the `app/llm.py` provider
abstraction) and Phase 2 (media library on R2). FastAPI + Next.js 14, same conventions.

## Conventions (do not deviate)
- Python `str | None`, Python 3.11. Reuse get_current_user and the slowapi limiter.
- ALL model calls go through `app/llm.py` — do not call a provider SDK directly.
- Frontend uses /api/* rewrite. Tokens: bg #0F0F0F, surface #1A1A1A, accent #E1306C,
  text #F5F5F5, muted #888888, border #2A2A2A.

## Model
- Use the SAME multimodal model as Phase 1: `meta-llama/llama-4-scout-17b-16e-instruct`
  (Llama 4 Scout on Groq) via app/llm.py. It accepts images in OpenAI-compatible format
  (image_url with a base64 data URL, or a public URL) and supports JSON/structured output.
- Scout's ~131K context easily handles a downscaled image + prompt. If vision quality ever
  proves insufficient, the abstraction allows overriding this one feature to Claude
  (claude-sonnet-4-6) by config.

## Endpoint — POST /ai/caption-from-image
- Body: media_asset_id (must belong to current_user), platform (str | None — if omitted,
  the model suggests the best-fit platform).
- Backend:
  1. Look up the media_asset for the current user (404 if not theirs).
  2. Fetch the image from R2.
  3. IMPORTANT: downscale to a max long edge ~1568px with Pillow before sending (saves
     tokens/cost; larger images get downscaled anyway).
  4. Send via app/llm.py as an OpenAI-compatible image input + a text prompt. Inject the
     user's stored brand voice if present.
- Return JSON ONLY (no prose/fences):
    { "suggested_platform": one of [instagram, x, tiktok, linkedin],
      "captions": [3 captions tuned to the chosen/suggested platform],
      "alt_text": short accessibility description }
  Parse safely: strip stray fences before JSON.parse; validate suggested_platform and fall
  back gracefully if invalid.
- Rate limit 15/hour.

## Frontend
- Once an image is attached, show "✨ Caption this image". On click, call the endpoint
  (with the selected platform, else let it suggest). Render the suggested platform as a
  badge, 3 captions as clickable chips that fill the caption field, alt_text shown subtly.
- If no platform was picked, choosing a chip also sets the suggested platform.
- Loading + error states themed with the tokens.

## Delivery
- No DB migration (reuses media_asset). Add Pillow to requirements.txt if missing.
- A local curl test against /ai/caption-from-image + the git add/commit/push commands.
