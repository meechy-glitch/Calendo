"use client"
import * as React from "react"
import { CalendarIcon, Info, Lock } from "lucide-react"
import { format } from "date-fns"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Calendar } from "@/components/ui/calendar"
import { useMediaQuery } from "@/hooks/useMediaQuery"
import { AICaptionButton } from "@/components/AICaptionButton"

export type Platform = "instagram" | "x" | "tiktok" | "linkedin"
export type PostStatus = "draft" | "scheduled" | "published"

const PLATFORM_COLORS = {
  instagram: "#833AB4",
  x: "#888888",
  tiktok: "#FE2C55",
  linkedin: "#0A66C2",
} as const

const PLATFORM_CHAR_LIMITS: Record<Platform, number> = {
  instagram: 2200,
  x: 280,
  tiktok: 2200,
  linkedin: 3000,
}

const PLATFORM_LABELS: Record<Platform, string> = {
  instagram: "Instagram",
  x: "X",
  tiktok: "TikTok",
  linkedin: "LinkedIn",
}

const PLATFORMS: { value: Platform; label: string }[] = [
  { value: "instagram", label: "Instagram" },
  { value: "x", label: "X" },
  { value: "tiktok", label: "TikTok" },
  { value: "linkedin", label: "LinkedIn" },
]

const STATUSES: { value: PostStatus; label: string }[] = [
  { value: "draft", label: "Draft" },
  { value: "scheduled", label: "Scheduled" },
  { value: "published", label: "Published" },
]

const MAX_NOTES_LENGTH = 500

const TIME_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "No time set" },
  ...Array.from({ length: 24 }, (_, h) =>
    [0, 30].map((m) => {
      const value = `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`
      const period = h >= 12 ? "PM" : "AM"
      const hour = h % 12 || 12
      return { value, label: `${hour}:${String(m).padStart(2, "0")} ${period}` }
    })
  ).flat(),
]

export interface PostData {
  id?: string
  title: string
  caption: string
  platform: Platform
  platforms?: Platform[]
  scheduledDate: Date
  status: PostStatus
  scheduledTime?: string
  notes?: string
}

export interface PostModalProps {
  isOpen: boolean
  mode: "create" | "edit"
  post?: PostData
  scheduledDate?: Date
  onSave: (postData: PostData) => void
  onDelete?: (postId: string) => void
  onClose: () => void
}

export function PostModal({ isOpen, mode, post, scheduledDate, onSave, onDelete, onClose }: PostModalProps) {
  const isMobile = useMediaQuery("(max-width: 767px)")
  const isPublished = mode === "edit" && post?.status === "published"
  const [title, setTitle] = React.useState("")
  const [caption, setCaption] = React.useState("")
  const [platform, setPlatform] = React.useState<Platform>("instagram")
  const [selectedPlatforms, setSelectedPlatforms] = React.useState<Platform[]>(["instagram"])
  const [date, setDate] = React.useState<Date | undefined>(undefined)
  const [status, setStatus] = React.useState<PostStatus>("draft")
  const [scheduledTime, setScheduledTime] = React.useState("")
  const [notes, setNotes] = React.useState("")
  const [calendarOpen, setCalendarOpen] = React.useState(false)

  React.useEffect(() => {
    if (isOpen) {
      if (post) {
        setTitle(post.title)
        setCaption(post.caption || "")
        setPlatform(post.platform)
        setSelectedPlatforms([post.platform])
        setDate(post.scheduledDate)
        setStatus(post.status)
        setScheduledTime(post.scheduledTime || "")
        setNotes(post.notes || "")
      } else {
        setTitle("")
        setCaption("")
        setPlatform("instagram")
        setSelectedPlatforms(["instagram"])
        setDate(scheduledDate || undefined)
        setStatus("draft")
        setScheduledTime("")
        setNotes("")
      }
    }
  }, [isOpen, post, scheduledDate])

  const effectiveLimit = React.useMemo(() => {
    const platforms = mode === "create" ? selectedPlatforms : [platform]
    if (platforms.length === 0) return PLATFORM_CHAR_LIMITS.instagram
    return Math.min(...platforms.map((p) => PLATFORM_CHAR_LIMITS[p]))
  }, [mode, selectedPlatforms, platform])

  const captionOverLimit = caption.length > effectiveLimit

  const togglePlatform = (p: Platform) => {
    setSelectedPlatforms((prev) => {
      if (prev.includes(p)) {
        // Don't allow deselecting the last one
        if (prev.length === 1) return prev
        return prev.filter((x) => x !== p)
      }
      return [...prev, p]
    })
  }

  const handleSave = () => {
    if (!title.trim() || !date) return
    if (mode === "create") {
      onSave({
        id: post?.id,
        title: title.trim(),
        caption: caption.trim(),
        platform: selectedPlatforms[0],
        platforms: selectedPlatforms,
        scheduledDate: date,
        status,
        scheduledTime: scheduledTime || undefined,
        notes: notes.trim() || undefined,
      })
    } else {
      onSave({
        id: post?.id,
        title: title.trim(),
        caption: caption.trim(),
        platform,
        scheduledDate: date,
        status,
        scheduledTime: scheduledTime || undefined,
        notes: notes.trim() || undefined,
      })
    }
    onClose()
  }

  const handleDelete = () => {
    if (post?.id && onDelete) {
      onDelete(post.id)
      onClose()
    }
  }

  const isValid = title.trim().length > 0 && date !== undefined

  const restrictivePlatform = React.useMemo(() => {
    const platforms = mode === "create" ? selectedPlatforms : [platform]
    if (platforms.length === 0) return null
    return platforms.reduce((min, p) =>
      PLATFORM_CHAR_LIMITS[p] < PLATFORM_CHAR_LIMITS[min] ? p : min
    )
  }, [mode, selectedPlatforms, platform])

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[480px] border-[#2A2A2A] flex flex-col max-h-[90dvh] overflow-x-hidden" style={{ backgroundColor: "#1A1A1A" }}>
        <DialogHeader className="flex-shrink-0">
          <DialogTitle className="flex items-center gap-2" style={{ color: "#F5F5F5" }}>
            {mode === "create" ? "Create Post" : isPublished ? (
              <>View Post <Lock className="h-4 w-4" style={{ color: "#888888" }} /></>
            ) : "Edit Post"}
          </DialogTitle>
        </DialogHeader>

        <div className={cn("flex flex-col gap-5 py-4 overflow-y-auto overflow-x-hidden flex-1 min-h-0 max-w-full", isPublished && "opacity-60")}>
          {isPublished && (
            <div
              className="flex items-center gap-2 rounded-md border px-3 py-2"
              style={{ borderColor: "#2A2A2A", backgroundColor: "#161616" }}
            >
              <Info className="h-4 w-4 shrink-0" style={{ color: "#888888" }} />
              <p className="text-sm" style={{ color: "#888888" }}>
                This post has been published and cannot be edited.
              </p>
            </div>
          )}
          <div className="flex flex-col gap-2">
            <Label htmlFor="title" style={{ color: "#F5F5F5" }}>
              Title <span style={{ color: "#E1306C" }}>*</span>
            </Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Enter post title"
              disabled={isPublished}
              className="border-[#2A2A2A] focus-visible:ring-[#E1306C]/50 disabled:opacity-60 disabled:cursor-not-allowed"
              style={{ backgroundColor: "#0F0F0F", color: "#F5F5F5" }}
            />
          </div>

          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="caption" style={{ color: "#F5F5F5" }}>Caption</Label>
              <span className="text-xs" style={{ color: captionOverLimit ? "#E1306C" : "#888888" }}>
                {caption.length}/{effectiveLimit}
              </span>
            </div>
            <Textarea
              id="caption"
              value={caption}
              onChange={(e) => setCaption(e.target.value)}
              placeholder="Write your caption..."
              rows={4}
              disabled={isPublished}
              className="resize-none border-[#2A2A2A] focus-visible:ring-[#E1306C]/50 disabled:opacity-60 disabled:cursor-not-allowed"
              style={{ backgroundColor: "#0F0F0F", color: "#F5F5F5" }}
            />
            {!isPublished && (
              <AICaptionButton
                platform={mode === "create" ? selectedPlatforms[0] : platform}
                idea={title.trim() || caption.trim()}
                disabled={isPublished}
                onSelectCaption={setCaption}
              />
            )}
            {captionOverLimit && restrictivePlatform && (
              <p className="text-xs" style={{ color: "#E1306C" }}>
                Exceeds {PLATFORM_LABELS[restrictivePlatform]} character limit
              </p>
            )}
          </div>

          <div className="flex flex-col gap-2">
            <Label style={{ color: "#F5F5F5" }}>Platform</Label>
            {mode === "create" ? (
              <div className="flex flex-col gap-2">
                {PLATFORMS.map((p) => {
                  const checked = selectedPlatforms.includes(p.value)
                  return (
                    <label
                      key={p.value}
                      className="flex items-center gap-3 cursor-pointer rounded-md border px-3 py-2 transition-colors w-full max-w-full"
                      style={{
                        borderColor: checked ? PLATFORM_COLORS[p.value] : "#2A2A2A",
                        backgroundColor: checked ? `${PLATFORM_COLORS[p.value]}14` : "#0F0F0F",
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => togglePlatform(p.value)}
                        className="sr-only"
                      />
                      <span
                        className="flex items-center justify-center w-4 h-4 rounded border flex-shrink-0"
                        style={{
                          borderColor: checked ? PLATFORM_COLORS[p.value] : "#555555",
                          backgroundColor: checked ? PLATFORM_COLORS[p.value] : "transparent",
                        }}
                      >
                        {checked && (
                          <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
                            <path d="M1 4L3.5 6.5L9 1" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        )}
                      </span>
                      <span className="size-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: PLATFORM_COLORS[p.value] }} />
                      <span className="text-sm" style={{ color: "#F5F5F5" }}>{p.label}</span>
                    </label>
                  )
                })}
              </div>
            ) : (
              <Select value={platform} onValueChange={(v) => setPlatform(v as Platform)}>
                <SelectTrigger disabled={isPublished} className="w-full border-[#2A2A2A] focus:ring-[#E1306C]/50 disabled:opacity-60 disabled:cursor-not-allowed" style={{ backgroundColor: "#0F0F0F", color: "#F5F5F5" }}>
                  <SelectValue>
                    <div className="flex items-center gap-2">
                      <span className="size-2.5 rounded-full" style={{ backgroundColor: PLATFORM_COLORS[platform] }} />
                      {PLATFORMS.find((p) => p.value === platform)?.label}
                    </div>
                  </SelectValue>
                </SelectTrigger>
                <SelectContent className="border-[#2A2A2A]" style={{ backgroundColor: "#1A1A1A" }}>
                  {PLATFORMS.map((p) => (
                    <SelectItem key={p.value} value={p.value} className="focus:bg-[#2A2A2A]" style={{ color: "#F5F5F5" }}>
                      <div className="flex items-center gap-2">
                        <span className="size-2.5 rounded-full" style={{ backgroundColor: PLATFORM_COLORS[p.value] }} />
                        {p.label}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          <div className="flex flex-col gap-2">
            <Label style={{ color: "#F5F5F5" }}>
              Scheduled Date <span style={{ color: "#E1306C" }}>*</span>
            </Label>
            {isMobile ? (
              <input
                type="date"
                value={date ? format(date, "yyyy-MM-dd") : ""}
                onChange={(e) => {
                  if (e.target.value) setDate(new Date(e.target.value + "T00:00:00"))
                  else setDate(undefined)
                }}
                disabled={isPublished}
                className="w-full rounded-md border border-[#2A2A2A] px-3 py-2 text-sm disabled:opacity-60 disabled:cursor-not-allowed"
                style={{ backgroundColor: "#0F0F0F", color: "#F5F5F5", colorScheme: "dark" }}
              />
            ) : (
              <Popover open={calendarOpen} onOpenChange={setCalendarOpen}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    disabled={isPublished}
                    className={cn("w-full justify-start text-left font-normal border-[#2A2A2A] disabled:opacity-60 disabled:cursor-not-allowed", !date && "text-muted-foreground")}
                    style={{ backgroundColor: "#0F0F0F", color: date ? "#F5F5F5" : "#888888" }}
                  >
                    <CalendarIcon className="mr-2 size-4" style={{ color: "#888888" }} />
                    {date ? format(date, "PPP") : "Pick a date"}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0 border-[#2A2A2A]" style={{ backgroundColor: "#1A1A1A" }} align="start">
                  <Calendar
                    mode="single"
                    selected={date}
                    onSelect={(selectedDate) => { setDate(selectedDate); setCalendarOpen(false) }}
                    initialFocus
                    className="[&_button]:text-[#F5F5F5] [&_.rdp-day_button:hover]:bg-[#2A2A2A] [&_.rdp-day_button[data-selected]]:bg-[#E1306C]"
                  />
                </PopoverContent>
              </Popover>
            )}
          </div>

          <div className="flex flex-col gap-2">
            <Label style={{ color: "#F5F5F5" }}>Status</Label>
            <Select value={status} onValueChange={(v) => setStatus(v as PostStatus)}>
              <SelectTrigger disabled={isPublished} className="w-full border-[#2A2A2A] focus:ring-[#E1306C]/50 disabled:opacity-60 disabled:cursor-not-allowed" style={{ backgroundColor: "#0F0F0F", color: "#F5F5F5" }}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="border-[#2A2A2A]" style={{ backgroundColor: "#1A1A1A" }}>
                {STATUSES.map((s) => (
                  <SelectItem key={s.value} value={s.value} className="focus:bg-[#2A2A2A]" style={{ color: "#F5F5F5" }}>
                    {s.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex flex-col gap-2">
            <Label style={{ color: "#F5F5F5" }}>Scheduled Time</Label>
            <Select value={scheduledTime || "__none__"} onValueChange={(v) => setScheduledTime(v === "__none__" ? "" : v)}>
              <SelectTrigger disabled={isPublished} className="w-full border-[#2A2A2A] focus:ring-[#E1306C]/50 disabled:opacity-60 disabled:cursor-not-allowed" style={{ backgroundColor: "#0F0F0F", color: scheduledTime ? "#F5F5F5" : "#888888" }}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="border-[#2A2A2A] max-h-60" style={{ backgroundColor: "#1A1A1A" }}>
                {TIME_OPTIONS.map((t) => (
                  <SelectItem key={t.value || "__none__"} value={t.value || "__none__"} className="focus:bg-[#2A2A2A]" style={{ color: t.value ? "#F5F5F5" : "#888888" }}>
                    {t.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="notes" style={{ color: "#F5F5F5" }}>Internal Notes</Label>
              <span className="text-xs" style={{ color: notes.length >= MAX_NOTES_LENGTH ? "#E1306C" : "#888888" }}>
                {notes.length}/{MAX_NOTES_LENGTH}
              </span>
            </div>
            <Textarea
              id="notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value.slice(0, MAX_NOTES_LENGTH))}
              placeholder="e.g. get client approval, use product shot 3, needs graphic from design team"
              rows={3}
              disabled={isPublished}
              className="resize-none border-[#2A2A2A] focus-visible:ring-[#E1306C]/50 disabled:opacity-60 disabled:cursor-not-allowed"
              style={{ backgroundColor: "#0F0F0F", color: "#F5F5F5" }}
            />
          </div>
        </div>

        <DialogFooter className="flex-row gap-2 sm:justify-between flex-shrink-0 border-t border-[#2A2A2A] pt-4">
          {mode === "edit" && onDelete && (
            <Button
              variant="outline"
              onClick={handleDelete}
              className="border-[#E1306C] text-[#E1306C] hover:bg-[#E1306C]/10 hover:text-[#E1306C]"
              style={{ backgroundColor: "transparent" }}
            >
              Delete
            </Button>
          )}
          <div className={cn("flex gap-2", (mode === "create" || isPublished) && "ml-auto")}>
            <Button
              variant="outline"
              onClick={onClose}
              className="border-[#2A2A2A] hover:bg-[#2A2A2A]"
              style={{ backgroundColor: "transparent", color: "#F5F5F5" }}
            >
              {isPublished ? "Close" : "Cancel"}
            </Button>
            {!isPublished && (
              <Button
                onClick={handleSave}
                disabled={!isValid}
                className="hover:opacity-90 disabled:opacity-50"
                style={{ backgroundColor: "#E1306C", color: "#F5F5F5" }}
              >
                Save
              </Button>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
