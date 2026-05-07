import * as React from "react"
import { ChevronLeft, ChevronRight, Plus, Check } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

// Platform colors
const PLATFORM_COLORS = {
  instagram: "#833AB4",
  x: "#888888",
  tiktok: "#FE2C55",
  linkedin: "#0A66C2",
} as const

export type Platform = keyof typeof PLATFORM_COLORS

export interface MobilePost {
  id: string
  title: string
  platform: Platform
  date: Date
  status?: "draft" | "scheduled" | "published"
}

export interface CalendarMobileProps {
  posts: MobilePost[]
  currentMonth: Date
  onDateClick: (date: Date) => void
  onPostClick: (post: MobilePost) => void
  onMonthChange?: (date: Date) => void
  onMarkPublished: (post: MobilePost) => void
}

const DAYS_OF_WEEK = ["M", "T", "W", "T", "F", "S", "S"]

function getDaysInMonth(year: number, month: number): Date[] {
  const days: Date[] = []
  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)

  let startDay = firstDay.getDay()
  startDay = startDay === 0 ? 6 : startDay - 1

  for (let i = startDay - 1; i >= 0; i--) {
    const date = new Date(year, month, -i)
    days.push(date)
  }

  for (let i = 1; i <= lastDay.getDate(); i++) {
    days.push(new Date(year, month, i))
  }

  const remainingDays = 7 - (days.length % 7)
  if (remainingDays < 7) {
    for (let i = 1; i <= remainingDays; i++) {
      days.push(new Date(year, month + 1, i))
    }
  }

  return days
}

function isSameDay(date1: Date, date2: Date): boolean {
  return (
    date1.getFullYear() === date2.getFullYear() &&
    date1.getMonth() === date2.getMonth() &&
    date1.getDate() === date2.getDate()
  )
}

function isSameMonth(date1: Date, date2: Date): boolean {
  return (
    date1.getFullYear() === date2.getFullYear() &&
    date1.getMonth() === date2.getMonth()
  )
}

function getPostPlatformsForDate(posts: MobilePost[], date: Date): Platform[] {
  const dayPosts = posts.filter((post) => isSameDay(post.date, date))
  const platforms = [...new Set(dayPosts.map((post) => post.platform))]
  return platforms
}

function StatusBadge({ status }: { status: MobilePost["status"] }) {
  const statusConfig = {
    draft: {
      label: "Draft",
      className: "bg-[#2A2A2A] text-[#888888] border-[#2A2A2A]",
    },
    scheduled: {
      label: "Scheduled",
      className: "bg-[#E1306C]/20 text-[#E1306C] border-[#E1306C]/30",
    },
    published: {
      label: "Published",
      className: "bg-green-500/20 text-green-400 border-green-500/30",
    },
  }

  const config = statusConfig[status || "draft"]

  return (
    <Badge variant="outline" className={cn("text-[10px]", config.className)}>
      {config.label}
    </Badge>
  )
}

function MobileDayCell({
  date,
  posts,
  isCurrentMonth,
  isToday,
  isSelected,
  onSelect,
}: {
  date: Date
  posts: MobilePost[]
  isCurrentMonth: boolean
  isToday: boolean
  isSelected: boolean
  onSelect: (date: Date) => void
}) {
  const platforms = getPostPlatformsForDate(posts, date)
  const maxDots = 3
  const visiblePlatforms = platforms.slice(0, maxDots)
  const hasMore = platforms.length > maxDots

  return (
    <button
      onClick={() => onSelect(date)}
      className={cn(
        "flex flex-col items-center gap-1 py-2 transition-colors",
        !isCurrentMonth && "opacity-30"
      )}
    >
      <span
        className={cn(
          "flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium transition-colors",
          isSelected && "bg-[#E1306C] text-white",
          isToday && !isSelected && "ring-1 ring-[#E1306C]/50",
          !isSelected && "text-[#F5F5F5] hover:bg-[#2A2A2A]"
        )}
      >
        {date.getDate()}
      </span>
      <div className="flex h-2 items-center gap-0.5">
        {visiblePlatforms.map((platform, index) => (
          <div
            key={index}
            className="h-1.5 w-1.5 rounded-full"
            style={{ backgroundColor: PLATFORM_COLORS[platform] }}
          />
        ))}
        {hasMore && (
          <span className="text-[8px] font-medium text-[#888888]">+</span>
        )}
      </div>
    </button>
  )
}

function PostListItem({
  post,
  onClick,
  onMarkPublished,
}: {
  post: MobilePost
  onClick: (post: MobilePost) => void
  onMarkPublished: (post: MobilePost) => void
}) {
  const color = PLATFORM_COLORS[post.platform]
  const isPublished = post.status === "published"

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={() => onClick(post)}
        className="flex flex-1 items-center gap-3 rounded-lg bg-[#1A1A1A] p-3 text-left transition-colors hover:bg-[#252525]"
      >
        <div
          className="w-1 self-stretch rounded-full"
          style={{ backgroundColor: color, minHeight: "40px" }}
        />
        <div className="flex flex-1 flex-col gap-1">
          <span
            className="text-sm font-medium"
            style={{
              color: "#F5F5F5",
              opacity: isPublished ? 0.6 : 1,
              textDecoration: isPublished ? "line-through" : "none",
            }}
          >
            {post.title}
          </span>
          <span className="text-xs capitalize" style={{ color: "#888888" }}>
            {post.platform}
          </span>
        </div>
        <StatusBadge status={post.status} />
      </button>

      {/* Mark as Published button — hidden if already published */}
      {!isPublished && (
        <button
          onClick={() => onMarkPublished(post)}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg transition-colors hover:bg-[#E1306C]/20"
          style={{ border: "1px solid #2A2A2A" }}
          title="Mark as Published"
        >
          <Check className="h-4 w-4" style={{ color: "#888888" }} />
        </button>
      )}
    </div>
  )
}

export function CalendarMobile({
  posts,
  currentMonth,
  onDateClick,
  onPostClick,
  onMonthChange,
  onMarkPublished,
}: CalendarMobileProps) {
  const [selectedDate, setSelectedDate] = React.useState<Date>(new Date())

  const year = currentMonth.getFullYear()
  const month = currentMonth.getMonth()
  const days = getDaysInMonth(year, month)
  const today = new Date()

  const monthName = currentMonth.toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
  })

  const selectedDatePosts = posts.filter((post) =>
    isSameDay(post.date, selectedDate)
  )

  const selectedDateFormatted = selectedDate.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  })

  const handlePrevMonth = () => {
    const newDate = new Date(year, month - 1, 1)
    onMonthChange?.(newDate)
  }

  const handleNextMonth = () => {
    const newDate = new Date(year, month + 1, 1)
    onMonthChange?.(newDate)
  }

  const handleSelectDate = (date: Date) => {
    setSelectedDate(date)
  }

  const handleAddPost = () => {
    onDateClick(selectedDate)
  }

  return (
    <div className="relative flex h-full flex-col bg-[#0F0F0F]">
      {/* Top Section - Compact Monthly Grid */}
      <div className="flex flex-col gap-2 border-b border-[#2A2A2A] p-4">
        {/* Month Navigation */}
        <div className="flex items-center justify-between">
          <Button
            variant="ghost"
            size="icon"
            onClick={handlePrevMonth}
            className="h-8 w-8 text-[#F5F5F5] hover:bg-[#2A2A2A]"
          >
            <ChevronLeft className="h-4 w-4" />
            <span className="sr-only">Previous month</span>
          </Button>
          <h2 className="text-base font-semibold text-[#F5F5F5]">{monthName}</h2>
          <Button
            variant="ghost"
            size="icon"
            onClick={handleNextMonth}
            className="h-8 w-8 text-[#F5F5F5] hover:bg-[#2A2A2A]"
          >
            <ChevronRight className="h-4 w-4" />
            <span className="sr-only">Next month</span>
          </Button>
        </div>

        {/* Days of week header */}
        <div className="grid grid-cols-7">
          {DAYS_OF_WEEK.map((day, index) => (
            <div
              key={index}
              className="py-1 text-center text-xs font-medium text-[#888888]"
            >
              {day}
            </div>
          ))}
        </div>

        {/* Compact Calendar Grid */}
        <div className="grid grid-cols-7">
          {days.map((date, index) => (
            <MobileDayCell
              key={index}
              date={date}
              posts={posts}
              isCurrentMonth={isSameMonth(date, currentMonth)}
              isToday={isSameDay(date, today)}
              isSelected={isSameDay(date, selectedDate)}
              onSelect={handleSelectDate}
            />
          ))}
        </div>
      </div>

      {/* Bottom Section - Selected Day Post List */}
      <div className="flex flex-1 flex-col gap-3 overflow-auto p-4">
        <h3 className="text-sm font-semibold text-[#F5F5F5]">
          {selectedDateFormatted}
        </h3>

        {selectedDatePosts.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-2 py-8">
            <p className="text-sm text-[#888888]">No posts</p>
            <p className="text-xs text-[#888888]">Tap + to add one</p>
          </div>
        ) : (
          <div
            className="flex flex-col gap-2"
            style={{ overflowY: "auto", maxHeight: "calc(100vh - 480px)", paddingBottom: "140px" }}
          >
            {selectedDatePosts.map((post) => (
              <PostListItem
                key={post.id}
                post={post}
                onClick={onPostClick}
                onMarkPublished={onMarkPublished}
              />
            ))}
          </div>
        )}
      </div>

      {/* Floating Add Button */}
      <button
        onClick={handleAddPost}
        className="fixed bottom-6 right-6 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-[#E1306C] text-white shadow-lg transition-transform hover:scale-105 active:scale-95"
      >
        <Plus className="h-6 w-6" />
        <span className="sr-only">Add post for selected date</span>
      </button>
    </div>
  )
}
