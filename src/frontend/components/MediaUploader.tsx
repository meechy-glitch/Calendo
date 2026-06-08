"use client"
import * as React from "react"
import { uploadToR2 } from "@/services/media"
import type { MediaAssetResponse } from "@/services/media"

export type { MediaAssetResponse }

const IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"]
const VIDEO_TYPES = ["video/mp4", "video/quicktime"]
const ALLOWED_TYPES = [...IMAGE_TYPES, ...VIDEO_TYPES]
const IMAGE_MAX = 8 * 1024 * 1024   // 8 MB
const VIDEO_MAX = 50 * 1024 * 1024  // 50 MB

export interface MediaItem {
  asset: MediaAssetResponse
  localUrl: string  // object URL for preview
}

interface MediaUploaderProps {
  items: MediaItem[]
  onChange: (items: MediaItem[]) => void
  disabled?: boolean
}

function isVideo(mimeType: string | null): boolean {
  return !!mimeType && VIDEO_TYPES.includes(mimeType)
}

function thumbnailUrl(item: MediaItem): string {
  if (item.asset.thumbnail_key && item.asset.public_url) {
    // Thumbnail key → replace the media key segment in public_url
    const base = item.asset.public_url.split("/users/")[0]
    return `${base}/${item.asset.thumbnail_key}`
  }
  return item.localUrl
}

function ProcessingBadge() {
  return (
    <div
      className="absolute inset-0 flex items-center justify-center text-xs font-medium"
      style={{ backgroundColor: "rgba(15,15,15,0.7)", color: "#F5F5F5" }}
    >
      Processing…
    </div>
  )
}

function PlayBadge() {
  return (
    <div
      className="absolute inset-0 flex items-center justify-center pointer-events-none"
      style={{ backgroundColor: "rgba(15,15,15,0.3)" }}
    >
      <div
        className="flex items-center justify-center w-8 h-8 rounded-full"
        style={{ backgroundColor: "rgba(225,48,108,0.85)" }}
      >
        <svg width="12" height="14" viewBox="0 0 12 14" fill="white">
          <path d="M1 1l10 6-10 6V1z" />
        </svg>
      </div>
    </div>
  )
}

function MediaThumb({
  item,
  index,
  total,
  onRemove,
  onDragStart,
  onDragOver,
  onDrop,
  disabled,
}: {
  item: MediaItem
  index: number
  total: number
  onRemove: (i: number) => void
  onDragStart: (i: number) => void
  onDragOver: (e: React.DragEvent, i: number) => void
  onDrop: (e: React.DragEvent, i: number) => void
  disabled: boolean
}) {
  const video = isVideo(item.asset.mime_type)
  const processing = item.asset.status === "processing"
  const thumb = thumbnailUrl(item)

  return (
    <div
      draggable={!disabled && total > 1}
      onDragStart={() => onDragStart(index)}
      onDragOver={(e) => onDragOver(e, index)}
      onDrop={(e) => onDrop(e, index)}
      className="relative rounded-md overflow-hidden border flex-shrink-0"
      style={{
        width: 80,
        height: 80,
        borderColor: "#2A2A2A",
        cursor: total > 1 && !disabled ? "grab" : "default",
      }}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={thumb} alt="" className="w-full h-full object-cover" />
      {video && !processing && <PlayBadge />}
      {processing && <ProcessingBadge />}
      {!disabled && (
        <button
          type="button"
          onClick={() => onRemove(index)}
          className="absolute top-0.5 right-0.5 flex items-center justify-center w-5 h-5 rounded-full text-xs font-bold hover:opacity-80"
          style={{ backgroundColor: "#0F0F0F", color: "#F5F5F5", border: "1px solid #2A2A2A" }}
        >
          ×
        </button>
      )}
      <div
        className="absolute bottom-0 left-0 right-0 flex items-center justify-center text-[9px]"
        style={{ backgroundColor: "rgba(15,15,15,0.65)", color: "#888" }}
      >
        {index + 1}/{total}
      </div>
    </div>
  )
}

export function MediaUploader({ items, onChange, disabled = false }: MediaUploaderProps) {
  const [dragging, setDragging] = React.useState(false)
  const [uploading, setUploading] = React.useState(false)
  const [progress, setProgress] = React.useState<number | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const [dragIndex, setDragIndex] = React.useState<number | null>(null)
  const inputRef = React.useRef<HTMLInputElement>(null)

  const handleFile = async (file: File) => {
    setError(null)
    if (!ALLOWED_TYPES.includes(file.type)) {
      setError("Supported: JPEG, PNG, WebP, MP4, MOV")
      return
    }
    const maxBytes = VIDEO_TYPES.includes(file.type) ? VIDEO_MAX : IMAGE_MAX
    if (file.size > maxBytes) {
      const limitMb = maxBytes / (1024 * 1024)
      setError(`File must be under ${limitMb} MB.`)
      return
    }
    const localUrl = URL.createObjectURL(file)
    setUploading(true)
    setProgress(0)
    try {
      const asset = await uploadToR2(file, setProgress)
      setProgress(null)
      onChange([...items, { asset, localUrl }])
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.")
    } finally {
      setUploading(false)
      setProgress(null)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    if (disabled || uploading) return
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
    e.target.value = ""
  }

  const handleRemove = (index: number) => {
    onChange(items.filter((_, i) => i !== index))
  }

  const handleDragStart = (index: number) => setDragIndex(index)

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault()
    if (dragIndex === null || dragIndex === index) return
    const next = [...items]
    const [moved] = next.splice(dragIndex, 1)
    next.splice(index, 0, moved)
    setDragIndex(index)
    onChange(next)
  }

  const handleDrop2 = (e: React.DragEvent, _index: number) => {
    e.preventDefault()
    setDragIndex(null)
  }

  return (
    <div className="flex flex-col gap-2">
      {items.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {items.map((item, i) => (
            <MediaThumb
              key={item.asset.id}
              item={item}
              index={i}
              total={items.length}
              onRemove={handleRemove}
              onDragStart={handleDragStart}
              onDragOver={handleDragOver}
              onDrop={handleDrop2}
              disabled={disabled}
            />
          ))}
        </div>
      )}

      {!disabled && (
        <div
          onClick={() => !uploading && inputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); if (!uploading) setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          className="flex flex-col items-center justify-center gap-1 rounded-md border-2 border-dashed px-4 py-4 text-sm transition-colors cursor-pointer"
          style={{
            borderColor: dragging ? "#E1306C" : "#2A2A2A",
            backgroundColor: dragging ? "#E1306C14" : "#0F0F0F",
            color: "#888888",
            opacity: uploading ? 0.6 : 1,
            pointerEvents: uploading ? "none" : "auto",
          }}
        >
          {uploading ? (
            <span className="text-xs" style={{ color: "#E1306C" }}>
              {progress !== null && progress < 100
                ? `Uploading ${progress}%…`
                : "Processing video…"}
            </span>
          ) : (
            <>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <circle cx="8.5" cy="8.5" r="1.5" />
                <path d="M21 15l-5-5L5 21" />
              </svg>
              <span>
                {items.length === 0
                  ? <>Drop media or <span style={{ color: "#E1306C" }}>browse</span></>
                  : <>Add another</>}
              </span>
              <span className="text-xs" style={{ color: "#555" }}>
                Image (8 MB) · Video MP4/MOV (50 MB)
              </span>
            </>
          )}
        </div>
      )}

      {progress !== null && (
        <div className="h-1 rounded-full overflow-hidden" style={{ backgroundColor: "#2A2A2A" }}>
          <div
            className="h-1 transition-all"
            style={{ width: `${progress}%`, backgroundColor: "#E1306C" }}
          />
        </div>
      )}

      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,video/mp4,video/quicktime"
        className="sr-only"
        onChange={handleInputChange}
      />
      {error && <p className="text-xs" style={{ color: "#E1306C" }}>{error}</p>}
    </div>
  )
}
