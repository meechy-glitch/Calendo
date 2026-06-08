"use client"
import * as React from "react"
import { uploadToR2 } from "@/services/media"

const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"]
const MAX_SIZE = 8 * 1024 * 1024

interface MediaUploaderProps {
  onUploaded: (mediaAssetId: number, publicUrl: string) => void
  onClear: () => void
  existingUrl?: string
  disabled?: boolean
}

export function MediaUploader({ onUploaded, onClear, existingUrl, disabled }: MediaUploaderProps) {
  const [dragging, setDragging] = React.useState(false)
  const [progress, setProgress] = React.useState<number | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const [preview, setPreview] = React.useState<string | null>(existingUrl ?? null)
  const inputRef = React.useRef<HTMLInputElement>(null)

  React.useEffect(() => {
    setPreview(existingUrl ?? null)
  }, [existingUrl])

  const handleFile = async (file: File) => {
    setError(null)
    if (!ALLOWED_TYPES.includes(file.type)) {
      setError("Only JPEG, PNG, or WebP images are allowed.")
      return
    }
    if (file.size > MAX_SIZE) {
      setError("File must be under 8 MB.")
      return
    }
    setPreview(URL.createObjectURL(file))
    setProgress(0)
    try {
      const asset = await uploadToR2(file, setProgress)
      setProgress(null)
      onUploaded(asset.id, asset.public_url ?? "")
    } catch (err) {
      setPreview(null)
      setProgress(null)
      setError(err instanceof Error ? err.message : "Upload failed.")
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    if (disabled) return
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
    e.target.value = ""
  }

  const handleClear = () => {
    setPreview(null)
    setError(null)
    setProgress(null)
    onClear()
  }

  if (preview) {
    return (
      <div className="relative w-full rounded-md overflow-hidden border" style={{ borderColor: "#2A2A2A" }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={preview} alt="Media preview" className="w-full max-h-48 object-cover" />
        {progress !== null && (
          <div className="absolute inset-x-0 bottom-0 h-1" style={{ backgroundColor: "#2A2A2A" }}>
            <div className="h-1 transition-all" style={{ width: `${progress}%`, backgroundColor: "#E1306C" }} />
          </div>
        )}
        {!disabled && progress === null && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute top-2 right-2 flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold hover:opacity-80"
            style={{ backgroundColor: "#0F0F0F", color: "#F5F5F5", border: "1px solid #2A2A2A" }}
          >
            ×
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-1">
      <div
        onClick={() => !disabled && inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); if (!disabled) setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className="flex flex-col items-center justify-center gap-1 rounded-md border-2 border-dashed px-4 py-5 text-sm transition-colors cursor-pointer"
        style={{
          borderColor: dragging ? "#E1306C" : "#2A2A2A",
          backgroundColor: dragging ? "#E1306C14" : "#0F0F0F",
          color: "#888888",
          opacity: disabled ? 0.5 : 1,
          pointerEvents: disabled ? "none" : "auto",
        }}
      >
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <circle cx="8.5" cy="8.5" r="1.5" />
          <path d="M21 15l-5-5L5 21" />
        </svg>
        <span>Drag &amp; drop an image, or <span style={{ color: "#E1306C" }}>browse</span></span>
        <span className="text-xs" style={{ color: "#555555" }}>JPEG · PNG · WebP · max 8 MB</span>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="sr-only"
        onChange={handleInputChange}
      />
      {error && <p className="text-xs" style={{ color: "#E1306C" }}>{error}</p>}
    </div>
  )
}
