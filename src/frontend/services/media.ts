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

export interface PresignResponse {
  upload_url: string
  media_asset_id: number
  storage_key: string
  public_url: string
  expires_in: number
}

export interface MediaAssetResponse {
  id: number
  storage_key: string
  public_url: string | null
  original_filename: string | null
  mime_type: string | null
  file_size_bytes: number | null
  width: number | null
  height: number | null
  duration_seconds: number | null
  thumbnail_key: string | null
  status: string
  created_at: string
  spec_warnings: Record<string, string[]> | null
}

export async function presignUpload(
  filename: string,
  contentType: string,
  sizeBytes: number,
): Promise<PresignResponse> {
  const res = await fetch(`${API_BASE}/media/presign`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ filename, content_type: contentType, size_bytes: sizeBytes }),
  })
  return handleResponse(res)
}

export async function confirmUpload(mediaAssetId: number): Promise<MediaAssetResponse> {
  const res = await fetch(`${API_BASE}/media/confirm`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ media_asset_id: mediaAssetId }),
  })
  return handleResponse(res)
}

export async function getMediaAsset(mediaAssetId: number): Promise<MediaAssetResponse> {
  const res = await fetch(`${API_BASE}/media/${mediaAssetId}`, { headers: getHeaders() })
  return handleResponse(res)
}

export async function uploadToR2(
  file: File,
  onProgress?: (pct: number) => void,
): Promise<MediaAssetResponse> {
  const { upload_url, media_asset_id } = await presignUpload(file.name, file.type, file.size)

  await new Promise<void>((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open("PUT", upload_url)
    xhr.setRequestHeader("Content-Type", file.type)
    if (onProgress) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100))
      }
    }
    xhr.onload = () =>
      xhr.status >= 200 && xhr.status < 300
        ? resolve()
        : reject(new Error(`Upload failed: ${xhr.status}`))
    xhr.onerror = () => reject(new Error("Upload network error"))
    xhr.send(file)
  })

  // confirm triggers ffmpeg processing for videos (synchronous on server)
  return confirmUpload(media_asset_id)
}
