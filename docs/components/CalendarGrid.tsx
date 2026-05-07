"use client"

import * as React from "react"
import { Check, ChevronLeft, ChevronRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

// Platform colors
const PLATFORM_COLORS = {
  instagram: "#833AB4",
  x: "#888888",
  tiktok: "#FE2C55",
  linkedin: "#0A66C2",
} as const

export type Platform = keyof typeof PLATFORM_COLORS

export type PostStatus = "draft" | "scheduled" | "published"

export interface Post {
  id: string
  title: string
  platform: Platform
  date: Date
  status?: PostStatus
}

export interface CalendoCalendarProps {
  posts: Post[]
  currentMonth: Date
  onDateClick: (date: Date) => void
  onPostClick: (post: Post) => void
  onMonthChange?: (date: Date) => void
}

const DAYS_OF_WEEK = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

function getDaysInMonth(year: number, month: number): Date[] {
  const days: Date[] = []
  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)

  // Get the day of week (0 = Sunday, 1 = Monday, etc.)
  // We want Monday as first day, so we adjust
  let startDay = firstDay.getDay()
  startDay = startDay === 0 ? 6 : startDay - 1 // Convert Sunday (0) to 6, others subtract 1

  // Add days from previous month to fill the first week
  for (let i = startDay - 1; i >= 0; i--) {
    const date = new Date(year, month, -i)
    days.push(date)
  }

  // Add all days of current month
  for (let i = 1; i <= lastDay.getDate(); i++) {
    days.push(new Date(year, month, i))
  }

  // Add days from next month to complete the last week
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

function PostChip({
  post,
  onClick,
}: {
  post: Post
  onClick: (post: Post) => void
}) {
  const color = PLATFORM_COLORS[post.platform]
  const status = post.status || "scheduled"

  // Style variations based on status
  const getChipStyles = (): React.CSSProperties => {
    switch (status) {
      case "draft":
        return {
          backgroundColor: `${color}B3`, // ~70% opacity
          border: `2px dashed ${color}`,
        }
      case "published":
        return {
          backgroundColor: color,
          opacity: 0.6,
        }
      case "scheduled":
      default:
        return {
          backgroundColor: color,
        }
    }
  }

  return (
    <button
      onClick={(e) => {
        e.stopPropagation()
        onClick(post)
      }}
      className={cn(
        "flex w-full items-center gap-1 truncate rounded-full px-2 py-0.5 text-left text-xs font-medium text-white transition-opacity hover:opacity-80",
        status === "draft" && "bg-transparent"
      )}
      style={getChipStyles()}
      title={`${post.title} (${post.platform}) - ${status}`}
    >
      {status === "published" && <Check className="h-3 w-3 shrink-0" />}
      <span className="truncate">{post.title}</span>
    </button>
  )
}

function DayCell({
  date,
  posts,
  isCurrentMonth,
  isToday,
  onDateClick,
  onPostClick,
}: {
  date: Date
  posts: Post[]
  isCurrentMonth: boolean
  isToday: boolean
  onDateClick: (date: Date) => void
  onPostClick: (post: Post) => void
}) {
  const dayPosts = posts.filter((post) => isSameDay(post.date, date))
  const maxVisiblePosts = 3
  const visiblePosts = dayPosts.slice(0, maxVisiblePosts)
  const remainingCount = dayPosts.length - maxVisiblePosts

  return (
    <button
      onClick={() => onDateClick(date)}
      className={cn(
        "calendo-surface calendo-border flex min-h-[100px] flex-col gap-1 rounded-lg border p-2 text-left transition-colors hover:bg-[#252525]",
        !isCurrentMonth && "opacity-40"
      )}
    >
      <span
        className={cn(
          "calendo-text flex h-7 w-7 items-center justify-center rounded-full text-sm font-medium",
          isToday && "calendo-accent text-white"
        )}
      >
        {date.getDate()}
      </span>
      <div className="flex flex-1 flex-col gap-1 overflow-hidden">
        {visiblePosts.map((post) => (
          <PostChip key={post.id} post={post} onClick={onPostClick} />
        ))}
        {remainingCount > 0 && (
          <span className="calendo-muted px-2 text-xs">
            +{remainingCount} more
          </span>
        )}
      </div>
    </button>
  )
}

export function CalendoCalendar({
  posts,
  currentMonth,
  onDateClick,
  onPostClick,
  onMonthChange,
}: CalendoCalendarProps) {
  const year = currentMonth.getFullYear()
  const month = currentMonth.getMonth()
  const days = getDaysInMonth(year, month)
  const today = new Date()

  const monthName = currentMonth.toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
  })

  const handlePrevMonth = () => {
    const newDate = new Date(year, month - 1, 1)
    onMonthChange?.(newDate)
  }

  const handleNextMonth = () => {
    const newDate = new Date(year, month + 1, 1)
    onMonthChange?.(newDate)
  }

  return (
    <div className="calendo-bg flex flex-col gap-4 rounded-xl p-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="calendo-text text-xl font-semibold">{monthName}</h2>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="icon"
            onClick={handlePrevMonth}
            className="calendo-surface calendo-border calendo-text hover:bg-[#252525]"
          >
            <ChevronLeft className="h-4 w-4" />
            <span className="sr-only">Previous month</span>
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={handleNextMonth}
            className="calendo-surface calendo-border calendo-text hover:bg-[#252525]"
          >
            <ChevronRight className="h-4 w-4" />
            <span className="sr-only">Next month</span>
          </Button>
        </div>
      </div>

      {/* Days of week header */}
      <div className="grid grid-cols-7 gap-2">
        {DAYS_OF_WEEK.map((day) => (
          <div
            key={day}
            className="calendo-muted py-2 text-center text-sm font-medium"
          >
            {day}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div className="grid grid-cols-7 gap-2">
        {days.map((date, index) => (
          <DayCell
            key={index}
            date={date}
            posts={posts}
            isCurrentMonth={isSameMonth(date, currentMonth)}
            isToday={isSameDay(date, today)}
            onDateClick={onDateClick}
            onPostClick={onPostClick}
          />
        ))}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-4 pt-2">
        <span className="calendo-muted text-xs font-medium">Platforms:</span>
        {Object.entries(PLATFORM_COLORS).map(([platform, color]) => (
          <div key={platform} className="flex items-center gap-1.5">
            <div
              className="h-3 w-3 rounded-full"
              style={{ backgroundColor: color }}
            />
            <span className="calendo-muted text-xs capitalize">{platform}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
