"use client"
import * as React from "react"
import { Sparkles } from "lucide-react"
import { generateCaptions } from "@/services/ai"

interface AICaptionButtonProps {
  platform: string
  idea: string
  disabled?: boolean
  onSelectCaption: (caption: string) => void
}

export function AICaptionButton({ platform, idea, disabled, onSelectCaption }: AICaptionButtonProps) {
  const [loading, setLoading] = React.useState(false)
  const [captions, setCaptions] = React.useState<string[]>([])
  const [error, setError] = React.useState<string | null>(null)

  const handleGenerate = async () => {
    if (!idea.trim() || idea.trim().length < 3) {
      setError("Add a title or idea (3+ characters) first")
      return
    }
    setLoading(true)
    setError(null)
    setCaptions([])
    try {
      const result = await generateCaptions(idea.trim(), platform)
      setCaptions(result.captions)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to generate captions")
    } finally {
      setLoading(false)
    }
  }

  const handleSelect = (caption: string) => {
    onSelectCaption(caption)
    setCaptions([])
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
        {loading ? "Generating…" : "Write with AI"}
      </button>

      {error && (
        <p className="text-xs" style={{ color: "#E1306C" }}>
          {error}
        </p>
      )}

      {captions.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <p className="text-xs" style={{ color: "#888888" }}>
            Click a caption to use it:
          </p>
          {captions.map((caption, i) => (
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
