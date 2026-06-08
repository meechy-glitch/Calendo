"use client"
import * as React from "react"
import { Sparkles } from "lucide-react"
import { captionFromImage } from "@/services/ai"

const PLATFORM_LABELS: Record<string, string> = {
  instagram: "Instagram",
  x: "X",
  tiktok: "TikTok",
  linkedin: "LinkedIn",
}

interface AIImageCaptionButtonProps {
  mediaAssetId: number
  platform: string | null
  disabled?: boolean
  onSelectCaption: (caption: string) => void
  onSelectPlatform: (platform: string) => void
}

interface CaptionResult {
  suggested_platform: string
  captions: string[]
  alt_text: string
}

export function AIImageCaptionButton({
  mediaAssetId,
  platform,
  disabled,
  onSelectCaption,
  onSelectPlatform,
}: AIImageCaptionButtonProps) {
  const [loading, setLoading] = React.useState(false)
  const [result, setResult] = React.useState<CaptionResult | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const calledWithPlatform = React.useRef<string | null>(null)

  const handleGenerate = async () => {
    setLoading(true)
    setError(null)
    setResult(null)
    calledWithPlatform.current = platform
    try {
      const data = await captionFromImage(mediaAssetId, platform ?? undefined)
      setResult(data)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to generate captions")
    } finally {
      setLoading(false)
    }
  }

  const handleSelect = (caption: string) => {
    onSelectCaption(caption)
    if (!calledWithPlatform.current && result) {
      onSelectPlatform(result.suggested_platform)
    }
    setResult(null)
  }

  return (
    <div className="flex flex-col gap-2">
      <button
        type="button"
        onClick={handleGenerate}
        disabled={disabled || loading}
        className="flex items-center gap-1.5 self-start rounded-md border px-3 py-1.5 text-xs font-medium transition-colors hover:border-[#E1306C] hover:text-[#E1306C] disabled:cursor-not-allowed disabled:opacity-50"
        style={{ backgroundColor: "transparent", borderColor: "#2A2A2A", color: "#888888" }}
      >
        <Sparkles size={12} />
        {loading ? "Analyzing image…" : "✨ Caption this image"}
      </button>

      {error && (
        <p className="text-xs" style={{ color: "#E1306C" }}>
          {error}
        </p>
      )}

      {result && (
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <span
              className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
              style={{ backgroundColor: "#E1306C22", color: "#E1306C", border: "1px solid #E1306C44" }}
            >
              {PLATFORM_LABELS[result.suggested_platform] ?? result.suggested_platform}
            </span>
            {result.alt_text && (
              <span
                className="text-xs truncate max-w-[200px]"
                style={{ color: "#555555" }}
                title={result.alt_text}
              >
                {result.alt_text}
              </span>
            )}
          </div>
          <p className="text-xs" style={{ color: "#888888" }}>
            Click a caption to use it:
          </p>
          {result.captions.map((caption, i) => (
            <button
              key={i}
              type="button"
              onClick={() => handleSelect(caption)}
              className="w-full rounded-md border px-3 py-2 text-left text-xs transition-colors hover:border-[#E1306C]"
              style={{
                backgroundColor: "#0F0F0F",
                borderColor: "#2A2A2A",
                color: "#F5F5F5",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {caption}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
