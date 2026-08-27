const API_BASE = "/api"

export async function forgotPasswordApi(email: string) {
  const res = await fetch(`${API_BASE}/auth/forgot-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }))
    throw new Error(err.detail || "Request failed")
  }
  return res.json()
}

export async function resetPasswordApi(token: string, new_password: string) {
  const res = await fetch(`${API_BASE}/auth/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, new_password }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }))
    throw new Error(err.detail || "Request failed")
  }
  return res.json()
}

export async function demoApi() {
  const res = await fetch(`${API_BASE}/auth/demo`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Demo failed" }))
    throw new Error(err.detail || "Demo failed")
  }
  return res.json()
}

export async function loginApi(email: string, password: string) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Login failed" }))
    throw new Error(err.detail || "Login failed")
  }
  return res.json()
}

export async function registerApi(email: string, password: string, name: string) {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, name }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Registration failed" }))
    throw new Error(err.detail || "Registration failed")
  }
  return res.json()
}

function authHeaders(): HeadersInit {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

export interface Me {
  id: number
  email: string
  /** Null for accounts created before names existed. */
  name: string | null
  lead_reminders_enabled: boolean
  created_at: string
}

export async function getMeApi(): Promise<Me> {
  const res = await fetch(`${API_BASE}/auth/me`, { headers: authHeaders() })
  if (!res.ok) throw new Error("Failed to fetch profile")
  return res.json()
}

export async function updateMeApi(
  data: { name?: string; lead_reminders_enabled?: boolean }
): Promise<Me> {
  const res = await fetch(`${API_BASE}/auth/me`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify(data),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to update settings" }))
    throw new Error(err.detail || "Failed to update settings")
  }
  return res.json()
}

/**
 * Permanently deletes the signed-in account. The backend resolves the target
 * from the bearer token, so there is nothing to pass and nothing to get wrong.
 */
export async function deleteMeApi(): Promise<void> {
  const res = await fetch(`${API_BASE}/auth/me`, {
    method: "DELETE",
    headers: authHeaders(),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to delete account" }))
    throw new Error(err.detail || "Failed to delete account")
  }
}

/** Wipes every trace of the session from this browser. */
export function clearAuthState(): void {
  if (typeof window === "undefined") return
  localStorage.removeItem("token")
  localStorage.removeItem("email")
}

/** "ada@example.com" -> "ada". Empty string when there is nothing usable. */
export function displayNameFrom(name: string | null | undefined, email: string | null | undefined): string {
  const trimmed = name?.trim()
  if (trimmed) return trimmed
  const localPart = email?.split("@")[0]?.trim()
  return localPart || ""
}
