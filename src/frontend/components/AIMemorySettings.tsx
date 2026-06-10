"use client"
import * as React from "react"
import { X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { getMemories, deleteMemory, clearMemories, type MemoryItem } from "@/services/ai"

interface AIMemorySettingsProps {
  isOpen: boolean
  onClose: () => void
}

const TYPE_LABEL: Record<string, string> = {
  fact: "fact",
  preference: "pref",
  summary: "sum",
}

export function AIMemorySettings({ isOpen, onClose }: AIMemorySettingsProps) {
  const [memories, setMemories] = React.useState<MemoryItem[]>([])
  const [loading, setLoading] = React.useState(false)
  const [clearing, setClearing] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    if (!isOpen) return
    setLoading(true)
    setError(null)
    getMemories()
      .then(setMemories)
      .catch(() => setError("Failed to load memories"))
      .finally(() => setLoading(false))
  }, [isOpen])

  const handleDelete = async (id: number) => {
    try {
      await deleteMemory(id)
      setMemories((prev) => prev.filter((m) => m.id !== id))
    } catch {
      setError("Failed to delete memory")
    }
  }

  const handleClearAll = async () => {
    if (!confirm("Clear all memories? This cannot be undone.")) return
    setClearing(true)
    setError(null)
    try {
      await clearMemories()
      setMemories([])
    } catch {
      setError("Failed to clear memories")
    } finally {
      setClearing(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        className="sm:max-w-[480px] border-[#2A2A2A] flex flex-col max-h-[85dvh]"
        style={{ backgroundColor: "#1A1A1A" }}
      >
        <DialogHeader className="flex-shrink-0">
          <DialogTitle style={{ color: "#F5F5F5" }}>What Calendo AI Remembers</DialogTitle>
        </DialogHeader>

        {loading ? (
          <div className="flex flex-1 items-center justify-center py-8">
            <p className="text-sm" style={{ color: "#888888" }}>Loading…</p>
          </div>
        ) : (
          <div className="flex flex-col gap-3 overflow-y-auto flex-1 min-h-0 py-2">
            <p className="text-xs" style={{ color: "#888888" }}>
              Facts and preferences the assistant has learned about you. Delete anything you don&apos;t want remembered.
            </p>

            {memories.length === 0 ? (
              <p className="py-6 text-center text-sm" style={{ color: "#555555" }}>
                No memories saved yet. Chat with the assistant to get started.
              </p>
            ) : (
              <ul className="flex flex-col gap-1.5">
                {memories.map((m) => (
                  <li
                    key={m.id}
                    className="flex items-start gap-2 rounded-md px-3 py-2"
                    style={{ backgroundColor: "#0F0F0F" }}
                  >
                    <span
                      className="mt-0.5 shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide"
                      style={{ backgroundColor: "#2A2A2A", color: "#888888" }}
                    >
                      {TYPE_LABEL[m.type] ?? m.type}
                    </span>
                    <span className="flex-1 text-sm leading-snug" style={{ color: "#F5F5F5" }}>
                      {m.content}
                    </span>
                    <button
                      onClick={() => handleDelete(m.id)}
                      className="mt-0.5 shrink-0 transition-colors hover:text-[#E1306C]"
                      style={{ color: "#555555" }}
                      aria-label="Delete memory"
                    >
                      <X size={14} />
                    </button>
                  </li>
                ))}
              </ul>
            )}

            {error && <p className="text-xs" style={{ color: "#E1306C" }}>{error}</p>}
          </div>
        )}

        <DialogFooter
          className="flex-shrink-0 border-t border-[#2A2A2A] pt-4"
          style={{ justifyContent: "space-between" }}
        >
          <Button
            variant="outline"
            onClick={handleClearAll}
            disabled={clearing || memories.length === 0}
            className="border-[#2A2A2A] hover:border-red-800 hover:text-red-400"
            style={{ backgroundColor: "transparent", color: "#888888" }}
          >
            {clearing ? "Clearing…" : "Clear all"}
          </Button>
          <Button
            variant="outline"
            onClick={onClose}
            className="border-[#2A2A2A] hover:bg-[#2A2A2A]"
            style={{ backgroundColor: "transparent", color: "#F5F5F5" }}
          >
            Done
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
