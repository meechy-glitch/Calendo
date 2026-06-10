# Calendo AI — Phase 6 (v1): Voice input

Adds voice input to the two places that matter most: the chat assistant panel and the
caption idea field. Builds on Phase 1 (the AI brain). Two-part implementation — start
with Part A (frontend only, zero backend, ships immediately), then add Part B (Groq Whisper
for broader browser support) as an enhancement. Same conventions throughout.

## Hard conventions
- Python `str | None`, Python 3.11. Alembic for schema changes (none needed here).
- Reuse get_current_user and slowapi limiter. Frontend uses /api/* rewrite.
- Design tokens: bg #0F0F0F, surface #1A1A1A, accent #E1306C, text #F5F5F5,
  muted #888888, border #2A2A2A.

## Part A — Browser Web Speech API (frontend only, no backend changes)
- Create a `useSpeechRecognition` hook that wraps the native `window.SpeechRecognition`
  / `window.webkitSpeechRecognition` API. Returns { transcript, isListening, supported,
  start, stop }. If the API is not available (Firefox, older browsers), `supported` is
  false and the mic button is hidden — graceful degradation, never an error.
- Language: default to `en-US`.

### Mic button on ChatPanel.tsx
- Add a mic icon button next to the chat send button.
- On click: toggle recording on/off. While recording, pulse the mic icon with the accent
  color (#E1306C) as a visual indicator.
- On transcript ready: fill the message input with the transcribed text. User can edit
  before sending — do NOT auto-send.
- If speech recognition is unsupported, hide the button entirely.

### Mic button on the caption idea field (PostModal.tsx / AICaptionButton.tsx)
- Add a mic icon next to the idea input field.
- On click: record → transcript fills the idea field. User can edit then hit
  "✨ Write with AI" as normal.
- Same unsupported = hidden behaviour.

## Part B — Groq Whisper transcription (backend enhancement)
Implement this AFTER Part A. Adds broader browser support (Firefox, mobile browsers where
Web Speech API is unavailable or unreliable) and higher transcription accuracy.

- Endpoint `POST /ai/transcribe`: accepts `multipart/form-data` with an `audio` file
  (webm/mp4/wav/m4a, cap ~5MB). Calls Groq's audio transcription API
  (`client.audio.transcriptions.create`, model `whisper-large-v3-turbo`). Returns
  `{ text: str }`. Rate limit 10/hour.
- Frontend fallback: when `useSpeechRecognition.supported` is false, show the mic button
  but use `MediaRecorder` to capture audio → send as FormData to `/api/ai/transcribe` →
  fill input with returned text. Show a loading indicator while transcribing.
- No new env vars needed (reuses GROQ_API_KEY).
- Add `groq` to requirements.txt if not already present (the Groq Python SDK, separate
  from the openai SDK used for chat). Or use the openai SDK pointed at Groq's audio
  endpoint — whichever the existing llm.py uses.

## Delivery
- No DB migration needed.
- Local test for Part B: record a short audio file and POST it to /ai/transcribe via curl
  with multipart/form-data. Confirm text is returned.
- Git add/commit/push commands.
