const API_BASE = "/api"

function getHeaders(): HeadersInit {
  const token = localStorage.getItem("token")
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

function handleUnauthorized() {
  localStorage.removeItem("token")
  localStorage.removeItem("email")
  window.location.href = "/login"
}

async function handleResponse(res: Response) {
  if (res.status === 401) {
    handleUnauthorized()
    throw new Error("Unauthorized")
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "An error occurred" }))
    throw new Error(err.detail || "Request failed")
  }
  return res.json()
}

export async function generateCaptions(
  idea: string,
  platform: string,
  brandVoice?: string,
): Promise<{ captions: string[] }> {
  const res = await fetch(`${API_BASE}/ai/caption`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ idea, platform, brand_voice: brandVoice ?? null }),
  })
  return handleResponse(res)
}

export async function rewriteCaption(
  caption: string,
  targetPlatforms: string[],
): Promise<{ rewrites: Record<string, string> }> {
  const res = await fetch(`${API_BASE}/ai/rewrite`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ caption, target_platforms: targetPlatforms }),
  })
  return handleResponse(res)
}

export interface ChatMessage {
  role: "user" | "assistant"
  content: string
}

export interface ChatChange {
  type: string
  id: number
  new_date?: string
}

export async function sendChat(
  messages: ChatMessage[],
): Promise<{ assistant_reply: string; changes: ChatChange[] }> {
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone
  const res = await fetch(`${API_BASE}/ai/chat`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ messages, timezone: tz }),
  })
  return handleResponse(res)
}

export async function getBrandVoice(): Promise<{
  tone: string | null
  dos: string | null
  donts: string | null
  sample_posts: string | null
  updated_at: string | null
}> {
  const res = await fetch(`${API_BASE}/ai/brand-voice`, { headers: getHeaders() })
  return handleResponse(res)
}

export async function upsertBrandVoice(data: {
  tone?: string
  dos?: string
  donts?: string
  sample_posts?: string
}) {
  const res = await fetch(`${API_BASE}/ai/brand-voice`, {
    method: "PUT",
    headers: getHeaders(),
    body: JSON.stringify(data),
  })
  return handleResponse(res)
}

export async function transcribeAudio(audioBlob: Blob): Promise<{ text: string }> {
  const token = localStorage.getItem("token")
  const formData = new FormData()
  formData.append("audio", audioBlob, "recording.webm")
  const res = await fetch(`${API_BASE}/ai/transcribe`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  })
  return handleResponse(res)
}

export async function captionFromImage(
  mediaAssetId: number,
  platform?: string,
): Promise<{ suggested_platform: string; captions: string[]; alt_text: string }> {
  const res = await fetch(`${API_BASE}/ai/caption-from-image`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ media_asset_id: mediaAssetId, platform: platform ?? null }),
  })
  return handleResponse(res)
}

export interface MemoryItem {
  id: number
  content: string
  type: string
  source: string
  created_at: string
}

export async function getMemories(): Promise<MemoryItem[]> {
  const res = await fetch(`${API_BASE}/ai/memory`, { headers: getHeaders() })
  return handleResponse(res)
}

export async function deleteMemory(id: number): Promise<{ deleted: boolean }> {
  const res = await fetch(`${API_BASE}/ai/memory/${id}`, {
    method: "DELETE",
    headers: getHeaders(),
  })
  return handleResponse(res)
}

export async function clearMemories(): Promise<{ cleared: number }> {
  const res = await fetch(`${API_BASE}/ai/memory`, {
    method: "DELETE",
    headers: getHeaders(),
  })
  return handleResponse(res)
}
