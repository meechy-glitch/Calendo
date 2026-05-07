import * as React from "react"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"

interface FeedbackButtonProps {
  onSubmit: (message: string) => void
}

export function FeedbackButton({ onSubmit }: FeedbackButtonProps) {
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
      {/* Floating Button */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-24 right-6 z-50 flex h-14 w-14 items-center justify-center rounded-full shadow-lg transition-all hover:scale-105 hover:shadow-xl focus:outline-none focus:ring-2 focus:ring-offset-2"
        style={{
          backgroundColor: "#E1306C",
          color: "#F5F5F5",
        }}
        aria-label="Send feedback"
      >
        {/* Speech Bubble Icon */}
        <svg
          className="h-6 w-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
          />
        </svg>
      </button>

      {/* Feedback Modal */}
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent
          className="border sm:max-w-md"
          style={{
            backgroundColor: "#1A1A1A",
            borderColor: "#2A2A2A",
          }}
        >
          <DialogHeader>
            <DialogTitle
              className="text-lg font-semibold"
              style={{ color: "#F5F5F5" }}
            >
              Send Feedback
            </DialogTitle>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label
                htmlFor="feedback-message"
                className="text-sm font-medium"
                style={{ color: "#F5F5F5" }}
              >
                Your message
              </Label>
              <Textarea
                id="feedback-message"
                placeholder="Tell us what you think, report a bug, or suggest a feature..."
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                rows={5}
                className="resize-none border focus:ring-2"
                style={{
                  backgroundColor: "#0F0F0F",
                  borderColor: "#2A2A2A",
                  color: "#F5F5F5",
                }}
                required
              />
              <p className="text-xs" style={{ color: "#888888" }}>
                We read every piece of feedback
              </p>
            </div>

            <div className="flex justify-end gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={handleCancel}
                className="border transition-colors hover:bg-opacity-10"
                style={{
                  backgroundColor: "transparent",
                  borderColor: "#2A2A2A",
                  color: "#F5F5F5",
                }}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                className="transition-colors hover:opacity-90"
                style={{
                  backgroundColor: "#E1306C",
                  color: "#F5F5F5",
                }}
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

