# Calendo AI — Phase 1: The AI brain (Groq-first, provider-agnostic)

Implement an AI layer for Calendo ("Calendo AI"). Existing FastAPI + Next.js 14 (App
Router, TS, Tailwind, shadcn/ui) app, Supabase Postgres, backend on Render, frontend on
Vercel. NO external platform dependencies — build first while approval clocks run. Follow
ALL existing conventions.

## Hard conventions (do not deviate)
- Python: use `str | None`, never `Optional[str]` (Python 3.11). Alembic for all schema.
- Reuse the existing JWT auth dependency (get_current_user) and slowapi limiter.
- Frontend uses the existing /api/* rewrite to reach the backend; do not add config.
- Design tokens: bg #0F0F0F, surface #1A1A1A, accent #E1306C, text #F5F5F5,
  muted #888888, border #2A2A2A. Platform colors: IG #833AB4, X #888888,
  TikTok #FE2C55, LinkedIn #0A66C2.

## LLM provider abstraction (IMPORTANT — build this first)
- Put ALL model calls behind a single module `app/llm.py`. No route calls a provider SDK
  directly. Expose async helpers, e.g.:
    - `async def complete(messages, *, tools=None, model=None, max_tokens=...) -> ...`
  that returns a normalized result (text + any tool calls).
- DEFAULT provider: **Groq**, via the official `openai` Python SDK pointed at
  `https://api.groq.com/openai/v1` (Groq is OpenAI-compatible). Use the ASYNC client.
- Model ID comes from env/config, never hardcoded in routes. DEFAULT to ONE multimodal
  model for everything (text + vision + tool use):
    - LLM_MODEL = `meta-llama/llama-4-scout-17b-16e-instruct`
      (Llama 4 Scout on Groq: natively multimodal, supports function calling + JSON/
      structured output, ~131K context, 8K max output, ~$0.11/$0.34 per 1M tokens.)
  Because Scout is multimodal, the SAME model handles captions, rewrite, the agentic
  assistant, AND Phase 3 image captioning — no separate vision model needed. (Optional:
  `llama-3.1-8b-instant` for ultra-cheap high-volume captions; override the agentic
  assistant to Claude only if tool-use reliability disappoints.)
- Env: GROQ_API_KEY (required). Optional ANTHROPIC_API_KEY to allow routing specific
  features to Claude later. The abstraction must let a single feature override the provider/
  model by config, so the agentic assistant can fall back to a stronger model if Groq's
  tool-use reliability is insufficient.
- NOTE: Groq has no prompt-caching discount — keep system prompts lean.

## Feature 1 — Caption assistant
POST /ai/caption. Body: idea (3-500 chars), platform, brand_voice (str | None). Returns 3
platform-tuned captions (IG warm+emoji+hashtags; X punchy <280; TikTok casual+hooky;
LinkedIn professional). Rate limit 20/hour. Validate platform; 400 on unknown. Frontend:
"✨ Write with AI" button on the post form -> 3 clickable chips that fill the caption field.

## Feature 2 — Platform rewrite
POST /ai/rewrite. Body: caption, target_platforms (list). Returns the message adapted per
platform (voice + char limits). Frontend: "Adapt for platforms" action on a post.

## Feature 3 — Brand voice memory
Table brand_voice (user_id FK unique, tone, dos, donts, sample_posts, updated_at). Alembic
migration (no hand edits). CRUD under /ai/brand-voice (get + upsert, user-scoped). Inject
stored brand voice into every caption/rewrite/chat generation when present. Simple settings UI.

## Feature 4 — Conversational assistant (agentic, tool use)
POST /ai/chat. Body: messages (full chat history). Run an agentic tool-use loop via
`app/llm.py` using OpenAI-style function calling (Groq native). Tools, ALL executed
server-side and scoped to current_user.id (model never supplies/sees a user id):
  - get_today() -> current date + user timezone
  - list_posts(month, platform?, status?) -> trimmed list (id, title, platform,
    scheduled_date, scheduled_time, status), capped at 50
  - create_post(title, caption, platform, scheduled_date, scheduled_time?, notes?)
  - update_post(post_id, ...optional fields)
  - reschedule_post(post_id, scheduled_date, scheduled_time?)
  - bulk_create_posts(posts: list)  (for "plan my week")
No delete tool.
Loop requirements:
  - Append tool results and re-call until a final text answer. MAX_ITERATIONS = 6;
    return the partial answer gracefully if exceeded.
  - Validate every tool input with Pydantic; on failure return the error AS the tool result
    so the model self-corrects — do not raise to the client.
  - Inject current date + user timezone into the system prompt. Rate limit 30/hour.
  - Return assistant_reply + a `changes` array (created/updated post ids) so the frontend
    refreshes the calendar.
Frontend: a chat panel (themed). Holds the full message history in React state, sends it
whole each turn. On non-empty `changes`, refresh the calendar.

## Wiring & delivery
- Register routers in main.py. Add `openai` (used for Groq) to requirements.txt.
- Generate the brand_voice Alembic migration + the exact command.
- Do NOT implement social publishing, Celery, or Redis — out of scope.
- After building: (1) local test commands (uvicorn + curl for /ai/caption and /ai/chat),
  (2) git add/commit/push commands. Remind me to set GROQ_API_KEY in Render before pushing.
