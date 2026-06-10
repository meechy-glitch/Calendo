# Calendo AI — Cross-session assistant memory

Give the chat assistant durable memory of each user across sessions — brand details,
recurring campaigns, posting preferences, ongoing projects — so it stops re-asking and feels
like it knows them. Builds on Phase 1 (the AI brain + app/llm.py). FRONTEND + small backend.

MVP DESIGN DECISION: no embeddings, no pgvector. Store memories as text and inject the recent
ones into the system prompt (same mechanism as Brand Voice). Semantic retrieval is a later
scale upgrade (see Out of scope). This keeps it cheap (no embedding API/key) and simple.

## Hard conventions
- Python `str | None`, Python 3.11. Alembic for ALL schema changes (no hand edits).
- Reuse get_current_user, slowapi limiter, and app/llm.py. Frontend uses /api/* rewrite.
- Design tokens: bg #0F0F0F, surface #1A1A1A, accent #E1306C, text #F5F5F5,
  muted #888888, border #2A2A2A.
- NOTE: Groq has no prompt caching, so keep memories concise and capped — they're re-sent
  every turn.

## Schema
- Table `memory`: id, user_id FK ON DELETE CASCADE, content TEXT, type TEXT
  ('fact' | 'preference' | 'summary'), source TEXT DEFAULT 'assistant', created_at TIMESTAMPTZ.
  Index on user_id. MATCH EXISTING PK TYPES. Alembic migration + exact upgrade command.

## Capture — a save_memory tool
- Add a `save_memory(content: str, type: str)` tool to the agentic loop, executed
  server-side, scoped to current_user.id (the model never supplies a user id).
- System prompt guidance: save DURABLE, reusable facts/preferences — the user's brand,
  recurring campaigns, tone preferences, ongoing projects, what they've decided. Do NOT save
  one-off task details or trivia. Save when the user says "remember that…" AND proactively
  when it learns something clearly durable.
- Dedup: before inserting, skip if a case-insensitive near-identical content already exists
  for that user.
- Cap at ~200 memories per user; if exceeded, drop the oldest.

## Recall — inject into the system prompt
- On every /ai/chat call, load the user's memories (most recent first, cap ~50 or a sensible
  token budget) and inject them into the system prompt as a "What you remember about this
  user:" block — mirror exactly how Brand Voice is already injected.

## Manage — user control (privacy, important)
- Endpoints (all user-scoped): GET /ai/memory (list), DELETE /ai/memory/{id} (delete one),
  DELETE /ai/memory (clear all).
- Settings UI: a "What Calendo AI remembers" section listing each memory with a delete (×)
  control and a "Clear all" button. Users must be able to see and remove what's stored.

## Out of scope (scale upgrade, do NOT build now)
- pgvector embeddings + semantic similarity retrieval. Add only when users accumulate enough
  memories that "most recent ~50" stops being sufficient. At that point: enable the pgvector
  extension, add an embedding column, embed memories via a cheap embedding API (e.g. OpenAI
  text-embedding-3-small or an open model via DeepInfra — Groq does not do embeddings), and
  retrieve the most RELEVANT memories per query instead of the most recent.

## Delivery
- Alembic migration + exact upgrade command. Register the tool + endpoints. Build the
  Settings UI section.
- Test: in a chat, say "remember that our brand voice is playful and we focus on Gen Z";
  confirm save_memory fires. Start a FRESH chat session and ask something that should use it;
  confirm the memory is reflected. Delete it from Settings and confirm it's gone.
- Give me the git add/commit/push commands (I commit myself — do NOT commit).
