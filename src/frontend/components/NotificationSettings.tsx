"use client"
import * as React from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { getMeApi, updateMeApi } from "@/services/auth"

interface NotificationSettingsProps {
  isOpen: boolean
  onClose: () => void
}

export function NotificationSettings({ isOpen, onClose }: NotificationSettingsProps) {
  const [leadReminders, setLeadReminders] = React.useState(false)
  const [loading, setLoading] = React.useState(false)
  const [saving, setSaving] = React.useState(false)
  const [saved, setSaved] = React.useState(false)

  React.useEffect(() => {
    if (!isOpen) return
    setLoading(true)
    getMeApi()
      .then((data) => setLeadReminders(data.lead_reminders_enabled))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [isOpen])

  const toggle = async () => {
    const next = !leadReminders
    setLeadReminders(next)
    setSaving(true)
    try {
      await updateMeApi({ lead_reminders_enabled: next })
      setSaved(true)
      setTimeout(() => setSaved(false), 1500)
    } catch {
      setLeadReminders(!next)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        className="max-w-sm"
        style={{ backgroundColor: "#1A1A1A", border: "1px solid #2A2A2A", color: "#F5F5F5" }}
      >
        <DialogHeader>
          <DialogTitle style={{ color: "#F5F5F5" }}>Notification settings</DialogTitle>
        </DialogHeader>

        {loading ? (
          <div className="py-4 text-center text-sm" style={{ color: "#888888" }}>
            Loading…
          </div>
        ) : (
          <div className="py-2">
            <label className="flex cursor-pointer items-center justify-between gap-4">
              <div>
                <div className="text-sm font-medium" style={{ color: "#F5F5F5" }}>
                  24-hour lead reminder
                </div>
                <div className="mt-0.5 text-xs" style={{ color: "#888888" }}>
                  Get a heads-up email the day before a post is scheduled
                </div>
              </div>
              <button
                role="switch"
                aria-checked={leadReminders}
                onClick={toggle}
                disabled={saving}
                className="relative inline-flex h-5 w-9 flex-shrink-0 rounded-full transition-colors"
                style={{
                  backgroundColor: leadReminders ? "#E1306C" : "#2A2A2A",
                  border: "1px solid",
                  borderColor: leadReminders ? "#E1306C" : "#444",
                }}
              >
                <span
                  className="absolute top-0.5 inline-block h-4 w-4 rounded-full transition-transform"
                  style={{
                    backgroundColor: "#F5F5F5",
                    transform: leadReminders ? "translateX(16px)" : "translateX(1px)",
                  }}
                />
              </button>
            </label>
            {saved && (
              <p className="mt-3 text-xs" style={{ color: "#E1306C" }}>
                Saved ✓
              </p>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
