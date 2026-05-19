"use client"
import { useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import { CalendoNavbar } from "@/components/Navbar"
import { CalendoCalendar, type Post, type Platform, type PostStatus } from "@/components/CalendarGrid"
import { CalendarMobile, type MobilePost } from "@/components/CalendarMobile"
import { PlatformFilter } from "@/components/PlatformFilter"
import { PostModal, type PostData } from "@/components/PostModal"
import { ExportButton } from "@/components/ExportButton"
import { FeedbackButton } from "@/components/FeedbackButton"
import { LoadingSkeleton, EmptyState } from "@/components/EmptyState"
import { Toast } from "@/components/Toast"
import { useMediaQuery } from "@/hooks/useMediaQuery"
import { getPosts, createPost, updatePost, deletePost, exportCSV } from "@/services/posts"
import { AnalyticsSummary } from "@/components/AnalyticsSummary"
import { ProtectedRoute } from "@/components/ProtectedRoute"

const ALL_PLATFORMS: Platform[] = ["instagram", "x", "tiktok", "linkedin"]

const PLATFORM_COLORS: Record<Platform, string> = {
  instagram: "#833AB4",
  x: "#888888",
  tiktok: "#FE2C55",
  linkedin: "#0A66C2",
}

const PLATFORM_LABELS: Record<Platform, string> = {
  instagram: "Instagram",
  x: "X",
  tiktok: "TikTok",
  linkedin: "LinkedIn",
}

interface ApiPost {
  id: number
  title: string
  caption: string | null
  platform: string
  scheduled_date: string
  status: string
  scheduled_time: string | null
  notes: string | null
}

type CalendarPost = Post & { _raw: ApiPost }

function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  )
}

function toCalendarPost(p: ApiPost): CalendarPost {
  return {
    id: String(p.id),
    title: p.title,
    platform: p.platform as Platform,
    date: new Date(p.scheduled_date + "T00:00:00"),
    status: p.status as PostStatus,
    scheduledTime: p.scheduled_time || undefined,
    _raw: p,
  }
}

function getMonthStr(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`
}

function toLocalDateString(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`
}

function DashboardContent() {
  const router = useRouter()
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [posts, setPosts] = useState<CalendarPost[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null)
  const [activePlatforms, setActivePlatforms] = useState<Platform[]>(ALL_PLATFORMS)
  const [modalOpen, setModalOpen] = useState(false)
  const [modalMode, setModalMode] = useState<"create" | "edit">("create")
  const [selectedDate, setSelectedDate] = useState<Date | undefined>()
  const [selectedPost, setSelectedPost] = useState<PostData | undefined>()

  const isMobile = useMediaQuery("(max-width: 767px)")
  const userEmail = typeof window !== "undefined" ? localStorage.getItem("email") || "" : ""

  const showToast = useCallback((message: string, type: "success" | "error") => {
    setToast({ message, type })
  }, [])

  const hideToast = useCallback(() => setToast(null), [])

  const fetchPosts = useCallback(async () => {
    setIsLoading(true)
    try {
      const month = getMonthStr(currentMonth)
      const data = await getPosts(month)
      setPosts((data || []).map(toCalendarPost))
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Failed to load posts", "error")
    } finally {
      setIsLoading(false)
    }
  }, [currentMonth, showToast])

  useEffect(() => {
    fetchPosts()
  }, [fetchPosts])

  const handleDateClick = (date: Date) => {
    setSelectedDate(date)
    setSelectedPost(undefined)
    setModalMode("create")
    setModalOpen(true)
  }

  const handlePostClick = (post: Post | MobilePost) => {
    const raw = (post as CalendarPost)._raw
    if (!raw) return
    setSelectedPost({
      id: String(raw.id),
      title: raw.title,
      caption: raw.caption || "",
      platform: raw.platform as Platform,
      scheduledDate: new Date(raw.scheduled_date + "T00:00:00"),
      status: raw.status as PostStatus,
      scheduledTime: raw.scheduled_time || undefined,
      notes: raw.notes || undefined,
    })
    setModalMode("edit")
    setModalOpen(true)
  }

  const handleSave = async (postData: PostData) => {
    const body = {
      title: postData.title,
      caption: postData.caption,
      platform: postData.platform,
      scheduled_date: toLocalDateString(postData.scheduledDate),
      status: postData.status,
      scheduled_time: postData.scheduledTime || null,
      notes: postData.notes || null,
    }

    if (modalMode === "create") {
      const tempId = `temp-${Date.now()}`
      const tempRaw: ApiPost = {
        id: 0,
        title: postData.title,
        caption: postData.caption || null,
        platform: postData.platform,
        scheduled_date: toLocalDateString(postData.scheduledDate),
        status: postData.status,
        scheduled_time: postData.scheduledTime || null,
        notes: postData.notes || null,
      }
      setPosts((prev) => [...prev, { ...toCalendarPost(tempRaw), id: tempId }])
      try {
        const created: ApiPost = await createPost(body)
        setPosts((prev) => prev.map((p) => (p.id === tempId ? toCalendarPost(created) : p)))
        showToast("Post scheduled ✓", "success")
      } catch (err: unknown) {
        setPosts((prev) => prev.filter((p) => p.id !== tempId))
        showToast(err instanceof Error ? err.message : "Failed to save post", "error")
      }
    } else if (postData.id) {
      const originalPost = posts.find((p) => p.id === postData.id)
      const tempRaw: ApiPost = {
        id: parseInt(postData.id),
        title: postData.title,
        caption: postData.caption || null,
        platform: postData.platform,
        scheduled_date: toLocalDateString(postData.scheduledDate),
        status: postData.status,
        scheduled_time: postData.scheduledTime || null,
        notes: postData.notes || null,
      }
      setPosts((prev) => prev.map((p) => (p.id === postData.id ? toCalendarPost(tempRaw) : p)))
      try {
        await updatePost(postData.id, body)
        showToast("Post updated ✓", "success")
      } catch (err: unknown) {
        if (originalPost) setPosts((prev) => prev.map((p) => (p.id === postData.id ? originalPost : p)))
        showToast(err instanceof Error ? err.message : "Failed to save post", "error")
      }
    }
  }

  const handleDelete = async (postId: string) => {
    const originalPost = posts.find((p) => p.id === postId)
    setPosts((prev) => prev.filter((p) => p.id !== postId))
    try {
      await deletePost(postId)
      showToast("Post deleted", "success")
    } catch (err: unknown) {
      if (originalPost) setPosts((prev) => [...prev, originalPost])
      showToast(err instanceof Error ? err.message : "Failed to delete post", "error")
    }
  }

  const handleLogout = () => {
    localStorage.removeItem("token")
    localStorage.removeItem("email")
    router.replace("/login")
  }

  const handleToday = () => setCurrentMonth(new Date())

  const handlePlatformToggle = (platform: Platform) => {
    setActivePlatforms((prev) =>
      prev.includes(platform) ? prev.filter((p) => p !== platform) : [...prev, platform]
    )
  }

  const handleMarkPublished = async (post: MobilePost) => {
    const originalPost = posts.find((p) => p.id === post.id)
    setPosts((prev) =>
      prev.map((p) => (p.id === post.id ? { ...p, status: "published" as PostStatus } : p))
    )
    try {
      await updatePost(post.id, { status: "published" })
      showToast("Marked as published ✓", "success")
    } catch (err: unknown) {
      if (originalPost) setPosts((prev) => prev.map((p) => (p.id === post.id ? originalPost : p)))
      showToast(err instanceof Error ? err.message : "Failed to update status", "error")
    }
  }

  const handleExport = async () => {
    try {
      await exportCSV(getMonthStr(currentMonth))
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Export failed", "error")
    }
  }

  const filteredPosts = posts.filter((p) => activePlatforms.includes(p.platform))

  const today = new Date()
  const isCurrentMonth =
    currentMonth.getFullYear() === today.getFullYear() &&
    currentMonth.getMonth() === today.getMonth()

  const todayPosts = posts.filter((p) => isSameDay(p.date, today))
  const allTodayPublished = todayPosts.length > 0 && todayPosts.every((p) => p.status === "published")
  const todayPlatforms = [...new Set(todayPosts.map((p) => p.platform))]

  return (
    <div style={{ backgroundColor: "#0F0F0F", minHeight: "100vh" }}>
      <CalendoNavbar
        userEmail={userEmail}
        currentMonth={currentMonth}
        onLogout={handleLogout}
        onTodayClick={handleToday}
      />

      <main className="mx-auto max-w-[1400px] px-4 pb-8 pt-16 md:px-6">
        {!isLoading && isCurrentMonth && (
          <div
            className="mb-6 rounded-lg border-l-4 px-4 py-3 text-sm"
            style={{
              backgroundColor: "#1A1A1A",
              borderLeftColor: "#E1306C",
              borderTop: "1px solid #2A2A2A",
              borderRight: "1px solid #2A2A2A",
              borderBottom: "1px solid #2A2A2A",
              color: "#F5F5F5",
            }}
          >
            {todayPosts.length === 0 ? (
              "Nothing scheduled for today. Click today's date to add a post."
            ) : allTodayPublished ? (
              `All done for today! ${todayPosts.length} post${todayPosts.length !== 1 ? "s" : ""} published ✓`
            ) : (
              <span className="flex flex-wrap items-center gap-1">
                <span>
                  You have {todayPosts.length} post{todayPosts.length !== 1 ? "s" : ""} going out today —
                </span>
                {todayPlatforms.map((platform, i) => (
                  <span key={platform} className="inline-flex items-center gap-1">
                    {i > 0 && <span style={{ color: "#888888" }}>·</span>}
                    <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: PLATFORM_COLORS[platform] }} />
                    <span>{PLATFORM_LABELS[platform]}</span>
                  </span>
                ))}
              </span>
            )}
          </div>
        )}

        <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <PlatformFilter
            activePlatforms={activePlatforms}
            onToggle={handlePlatformToggle}
            onSelectAll={() => setActivePlatforms(ALL_PLATFORMS)}
          />
          <ExportButton onExport={handleExport} />
        </div>

        {isLoading ? (
          <LoadingSkeleton />
        ) : (
          <>
            <AnalyticsSummary posts={filteredPosts} />
            {isMobile ? (
              <CalendarMobile
                posts={filteredPosts}
                currentMonth={currentMonth}
                onDateClick={handleDateClick}
                onPostClick={handlePostClick}
                onMonthChange={setCurrentMonth}
                onMarkPublished={handleMarkPublished}
              />
            ) : (
              <>
                <CalendoCalendar
                  posts={filteredPosts}
                  currentMonth={currentMonth}
                  onDateClick={handleDateClick}
                  onPostClick={handlePostClick}
                  onMonthChange={setCurrentMonth}
                />
                {filteredPosts.length === 0 && (
                  <div className="mt-4">
                    <EmptyState />
                  </div>
                )}
              </>
            )}
          </>
        )}
      </main>

      <PostModal
        isOpen={modalOpen}
        mode={modalMode}
        post={selectedPost}
        scheduledDate={selectedDate}
        onSave={handleSave}
        onDelete={modalMode === "edit" ? handleDelete : undefined}
        onClose={() => setModalOpen(false)}
      />

      <FeedbackButton onSubmit={() => {}} />

      {toast && <Toast message={toast.message} type={toast.type} onClose={hideToast} />}
    </div>
  )
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  )
}
