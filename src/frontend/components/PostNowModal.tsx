"use client"
import * as React from "react"
import { Download, Copy, Check, ExternalLink, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { getHandoff, markPosted, skipPost } from "@/services/posts"

const PLATFORM_COLORS: Record<string, string> = {
  instagram: "#833AB4",
  x: "#888888",
  tiktok: "#FE2C55",
  linkedin: "#0A66C2",
  facebook: "#1877F2",
}

const PLATFORM_LABELS: Record<string, string> = {
  instagram: "Instagram",
  x: "X",
  tiktok: "TikTok",
  linkedin: "LinkedIn",
  facebook: "Facebook",
}

interface HandoffData {
  post_id: number
  caption: string | null
  platform: string
  media: Array<{ public_url: string | null; download_url: string | null; mime_type: string | null }>
  platform_action: { type: string; url: string; note: string | null }
  status: string
}

interface PostNowModalProps {
  postId: number | null
  onClose: () => void
  onDone: () => void
}

export function PostNowModal({ postId, onClose, onDone }: PostNowModalProps) {
  const [data, setData] = React.useState<HandoffData | null>(null)
  const [loading, setLoading] = React.useState(false)
  const [postedUrl, setPostedUrl] = React.useState("")
  const [captionCopied, setCaptionCopied] = React.useState(false)
  const [submitting, setSubmitting] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    if (!postId) return
    setLoading(true)
    setError(null)
    setPostedUrl("")
    setCaptionCopied(false)
    getHandoff(postId)
      .then(setData)
      .catch(() => setError("Failed to load post details"))
      .finally(() => setLoading(false))
  }, [postId])

  const handleCopyCaption = () => {
    if (!data?.caption) return
    navigator.clipboard.writeText(data.caption)
    setCaptionCopied(true)
    setTimeout(() => setCaptionCopied(false), 2000)
  }

  const handleMarkPosted = async () => {
    if (!postId) return
    setSubmitting(true)
    try {
      await markPosted(postId, postedUrl || undefined)
      onDone()
    } catch {
      setError("Failed to mark as posted")
    } finally {
      setSubmitting(false)
    }
  }

  const handleSkip = async () => {
    if (!postId) return
    setSubmitting(true)
    try {
      await skipPost(postId)
      onDone()
    } catch {
      setError("Failed to skip post")
    } finally {
      setSubmitting(false)
    }
  }

  const platformColor = data ? (PLATFORM_COLORS[data.platform] ?? "#888888") : "#888888"
  const platformLabel = data ? (PLATFORM_LABELS[data.platform] ?? data.platform) : ""

  return (
    <Dialog open={!!postId} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        className="max-w-lg"
        style={{ backgroundColor: "#1A1A1A", border: "1px solid #2A2A2A", color: "#F5F5F5" }}
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2" style={{ color: "#F5F5F5" }}>
            <span
              className="inline-block h-2.5 w-2.5 rounded-full flex-shrink-0"
              style={{ backgroundColor: platformColor }}
            />
            Post to {platformLabel}
          </DialogTitle>
        </DialogHeader>

        {loading && (
          <div className="py-8 text-center text-sm" style={{ color: "#888888" }}>
            Loading…
          </div>
        )}

        {error && (
          <div className="rounded px-3 py-2 text-sm" style={{ backgroundColor: "#2A0A0A", color: "#ff6b6b" }}>
            {error}
          </div>
        )}

        {data && !loading && (
          <div className="space-y-4">
            {/* Caption */}
            <div>
              <div className="mb-1 flex items-center justify-between">
                <Label style={{ color: "#888888", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  Caption
                </Label>
                <button
                  onClick={handleCopyCaption}
                  className="flex items-center gap-1 rounded px-2 py-1 text-xs transition-colors hover:bg-[#2A2A2A]"
                  style={{ color: captionCopied ? "#E1306C" : "#888888" }}
                >
                  {captionCopied ? <Check size={12} /> : <Copy size={12} />}
                  {captionCopied ? "Copied!" : "Copy"}
                </button>
              </div>
              <div
                className="max-h-32 overflow-y-auto rounded p-3 text-sm"
                style={{ backgroundColor: "#0F0F0F", border: "1px solid #2A2A2A", color: "#F5F5F5", whiteSpace: "pre-wrap" }}
              >
                {data.caption || <span style={{ color: "#888888" }}>(no caption)</span>}
              </div>
            </div>

            {/* Media */}
            {data.media.length > 0 && (
              <div>
                <Label style={{ color: "#888888", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  Media
                </Label>
                <div className="mt-1 flex flex-wrap gap-2">
                  {data.media.map((item, i) =>
                    item.public_url ? (
                      <a
                        key={i}
                        href={item.download_url ?? item.public_url}
                        download
                        className="group relative flex items-center gap-1.5 rounded border px-3 py-1.5 text-xs transition-colors hover:border-[#E1306C]"
                        style={{ borderColor: "#2A2A2A", color: "#888888" }}
                      >
                        <Download size={12} className="group-hover:text-[#E1306C]" />
                        {item.mime_type?.startsWith("video/") ? "Video" : "Image"} {i + 1}
                      </a>
                    ) : null
                  )}
                </div>
              </div>
            )}

            {/* Platform action */}
            <div
              className="rounded p-3 text-sm"
              style={{ backgroundColor: "#0F0F0F", border: "1px solid #2A2A2A" }}
            >
              {data.platform_action.type === "intent" || data.platform_action.type === "share" ? (
                <a
                  href={data.platform_action.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 font-medium hover:underline"
                  style={{ color: platformColor }}
                >
                  <ExternalLink size={13} />
                  Open {platformLabel} with caption pre-filled
                </a>
              ) : (
                <a
                  href={data.platform_action.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 font-medium hover:underline"
                  style={{ color: platformColor }}
                >
                  <ExternalLink size={13} />
                  Open {platformLabel} app
                </a>
              )}
              {data.platform_action.note && (
                <p className="mt-1" style={{ color: "#888888", fontSize: "11px" }}>
                  {data.platform_action.note}
                </p>
              )}
            </div>

            {/* Optional live URL */}
            <div>
              <Label htmlFor="posted-url" style={{ color: "#888888", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Live URL (optional)
              </Label>
              <Input
                id="posted-url"
                value={postedUrl}
                onChange={(e) => setPostedUrl(e.target.value)}
                placeholder="https://…"
                className="mt-1 text-sm"
                style={{
                  backgroundColor: "#0F0F0F",
                  border: "1px solid #2A2A2A",
                  color: "#F5F5F5",
                }}
              />
            </div>

            {/* Actions */}
            <div className="flex gap-2 pt-1">
              <Button
                onClick={handleMarkPosted}
                disabled={submitting}
                className="flex-1 font-medium"
                style={{ backgroundColor: "#E1306C", color: "#F5F5F5", border: "none" }}
              >
                {submitting ? "Saving…" : "Mark as posted"}
              </Button>
              <Button
                onClick={handleSkip}
                disabled={submitting}
                variant="ghost"
                className="text-sm"
                style={{ color: "#888888" }}
              >
                Skip
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
