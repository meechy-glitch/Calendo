"use client"
import * as React from "react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"

interface FeedbackButtonProps {
  onSubmit: (message: string) => void
  variant?: "link" | "settings"
}

export function FeedbackButton({ onSubmit, variant = "settings" }: FeedbackButtonProps) {
  const [isOpen, setIsOpen] = React.useState(false)
  const [message, setMessage] = React.useState("")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (message.trim()) {
      onSubmit(message.trim())
      setMessage("")
      setIsOpen(false)
    }
  }

  const handleCancel = () => {
    setMessage("")
    setIsOpen(false)
  }

  return (
    <>
      {variant === "link" ? (
        <button
          onClick={() => setIsOpen(true)}
          style={{
            color: "#555555",
            fontSize: "12px",
            textDecoration: "underline",
            textUnderlineOffset: "3px",
            textDecorationColor: "rgba(85,85,85,0.5)",
            background: "none",
            border: "none",
            cursor: "pointer",
            padding: 0,
          }}
        >
          Feedback
        </button>
      ) : (
        <button
          onClick={() => setIsOpen(true)}
          className="rounded-lg border px-4 py-2 text-sm font-medium transition-colors hover:border-[#E1306C] hover:text-[#E1306C]"
          style={{ backgroundColor: "transparent", borderColor: "#2A2A2A", color: "#888888" }}
        >
          Send Feedback
        </button>
      )}

      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent
          className="border sm:max-w-md"
          style={{ backgroundColor: "#1A1A1A", borderColor: "#2A2A2A" }}
        >
          <DialogHeader>
            <DialogTitle className="text-lg font-semibold" style={{ color: "#F5F5F5" }}>
              Send Feedback
            </DialogTitle>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="feedback-message" className="text-sm font-medium" style={{ color: "#F5F5F5" }}>
                Your message
              </Label>
              <Textarea
                id="feedback-message"
                placeholder="Tell us what you think, report a bug, or suggest a feature..."
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                rows={5}
                className="resize-none border focus:ring-2"
                style={{ backgroundColor: "#0F0F0F", borderColor: "#2A2A2A", color: "#F5F5F5" }}
                required
              />
              <p className="text-xs" style={{ color: "#888888" }}>We read every piece of feedback</p>
            </div>

            <div className="flex justify-end gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={handleCancel}
                className="border transition-colors hover:bg-opacity-10"
                style={{ backgroundColor: "transparent", borderColor: "#2A2A2A", color: "#F5F5F5" }}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                className="transition-colors hover:opacity-90"
                style={{ backgroundColor: "#E1306C", color: "#F5F5F5" }}
                disabled={!message.trim()}
              >
                Submit
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </>
  )
}
