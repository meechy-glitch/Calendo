"use client"
import * as React from "react"
import { X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { getBrandVoice, upsertBrandVoice } from "@/services/ai"

interface BrandVoiceSettingsProps {
  isOpen: boolean
  onClose: () => void
}

export function BrandVoiceSettings({ isOpen, onClose }: BrandVoiceSettingsProps) {
  const [tone, setTone] = React.useState("")
  const [dos, setDos] = React.useState("")
  const [donts, setDonts] = React.useState("")
  const [samplePosts, setSamplePosts] = React.useState("")
  const [loading, setLoading] = React.useState(false)
  const [saving, setSaving] = React.useState(false)
  const [saved, setSaved] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    if (!isOpen) return
    setLoading(true)
    setError(null)
    getBrandVoice()
      .then((data) => {
        setTone(data.tone ?? "")
        setDos(data.dos ?? "")
        setDonts(data.donts ?? "")
        setSamplePosts(data.sample_posts ?? "")
      })
      .catch(() => setError("Failed to load brand voice settings"))
      .finally(() => setLoading(false))
  }, [isOpen])

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      await upsertBrandVoice({
        tone: tone || undefined,
        dos: dos || undefined,
        donts: donts || undefined,
        sample_posts: samplePosts || undefined,
      })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save")
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        className="sm:max-w-[480px] border-[#2A2A2A] flex flex-col max-h-[85dvh]"
        style={{ backgroundColor: "#1A1A1A" }}
      >
        <DialogHeader className="flex-shrink-0">
          <DialogTitle style={{ color: "#F5F5F5" }}>Brand Voice</DialogTitle>
        </DialogHeader>

        {loading ? (
          <div className="flex flex-1 items-center justify-center py-8">
            <p className="text-sm" style={{ color: "#888888" }}>Loading…</p>
          </div>
        ) : (
          <div className="flex flex-col gap-4 overflow-y-auto flex-1 min-h-0 py-2">
            <p className="text-xs" style={{ color: "#888888" }}>
              Your brand voice is automatically injected into every caption, rewrite, and chat generation.
            </p>

            <div className="flex flex-col gap-2">
              <Label style={{ color: "#F5F5F5" }}>Tone</Label>
              <Textarea
                value={tone}
                onChange={(e) => setTone(e.target.value)}
                placeholder="e.g. playful, bold, witty, professional"
                rows={2}
                className="resize-none border-[#2A2A2A] focus-visible:ring-[#E1306C]/50"
                style={{ backgroundColor: "#0F0F0F", color: "#F5F5F5" }}
              />
            </div>

            <div className="flex flex-col gap-2">
              <Label style={{ color: "#F5F5F5" }}>Do</Label>
              <Textarea
                value={dos}
                onChange={(e) => setDos(e.target.value)}
                placeholder="e.g. use casual language, include calls to action, mention product benefits"
                rows={3}
                className="resize-none border-[#2A2A2A] focus-visible:ring-[#E1306C]/50"
                style={{ backgroundColor: "#0F0F0F", color: "#F5F5F5" }}
              />
            </div>

            <div className="flex flex-col gap-2">
              <Label style={{ color: "#F5F5F5" }}>{"Don't"}</Label>
              <Textarea
                value={donts}
                onChange={(e) => setDonts(e.target.value)}
                placeholder="e.g. avoid jargon, don't be overly formal, never make pricing claims"
                rows={3}
                className="resize-none border-[#2A2A2A] focus-visible:ring-[#E1306C]/50"
                style={{ backgroundColor: "#0F0F0F", color: "#F5F5F5" }}
              />
            </div>

            <div className="flex flex-col gap-2">
              <Label style={{ color: "#F5F5F5" }}>Sample Posts</Label>
              <Textarea
                value={samplePosts}
                onChange={(e) => setSamplePosts(e.target.value)}
                placeholder="Paste 1-2 example posts that capture your voice…"
                rows={4}
                className="resize-none border-[#2A2A2A] focus-visible:ring-[#E1306C]/50"
                style={{ backgroundColor: "#0F0F0F", color: "#F5F5F5" }}
              />
            </div>

            {error && <p className="text-xs" style={{ color: "#E1306C" }}>{error}</p>}
          </div>
        )}

        <DialogFooter className="flex-shrink-0 border-t border-[#2A2A2A] pt-4">
          <Button
            variant="outline"
            onClick={onClose}
            className="border-[#2A2A2A] hover:bg-[#2A2A2A]"
            style={{ backgroundColor: "transparent", color: "#F5F5F5" }}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={saving || loading}
            className="hover:opacity-90"
            style={{ backgroundColor: "#E1306C", color: "#F5F5F5" }}
          >
            {saved ? "Saved ✓" : saving ? "Saving…" : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
