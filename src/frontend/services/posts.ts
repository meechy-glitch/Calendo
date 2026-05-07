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
  if (res.status === 204) return null
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "An error occurred" }))
    throw new Error(err.detail || "Request failed")
  }
  return res.json()
}

export async function getPosts(month?: string) {
  const url = month ? `${API_BASE}/posts?month=${month}` : `${API_BASE}/posts`
  const res = await fetch(url, { headers: getHeaders() })
  return handleResponse(res)
}

export async function createPost(data: Record<string, unknown>) {
  const res = await fetch(`${API_BASE}/posts`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify(data),
  })
  return handleResponse(res)
}

export async function updatePost(id: string | number, data: Record<string, unknown>) {
  const res = await fetch(`${API_BASE}/posts/${id}`, {
    method: "PUT",
    headers: getHeaders(),
    body: JSON.stringify(data),
  })
  return handleResponse(res)
}

export async function deletePost(id: string | number) {
  const res = await fetch(`${API_BASE}/posts/${id}`, {
    method: "DELETE",
    headers: getHeaders(),
  })
  return handleResponse(res)
}

export async function exportCSV(month: string) {
  const token = localStorage.getItem("token")
  const res = await fetch(`${API_BASE}/posts/export/csv?month=${month}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (res.status === 401) {
    handleUnauthorized()
    throw new Error("Unauthorized")
  }
  if (!res.ok) throw new Error("Export failed")
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = `calendo-posts-${month}.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
