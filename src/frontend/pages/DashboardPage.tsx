import { useState, useEffect, useCallback } from "react"
import { CalendoNavbar } from "../components/Navbar"
import {
  CalendoCalendar,
  type Post,
  type Platform,
  type PostStatus,
} from "../components/CalendarGrid"
import { CalendarMobile, type MobilePost } from "../components/CalendarMobile"
import { PlatformFilter } from "../components/PlatformFilter"
import { PostModal, type PostData } from "../components/PostModal"
import { ExportButton } from "../components/ExportButton"
import { FeedbackButton } from "../components/FeedbackButton"
import { LoadingSkeleton, EmptyState } from "../components/EmptyState"
import { ErrorToast } from "../components/ErrorToast"
import { useMediaQuery } from "../hooks/useMediaQuery"
import { getPosts, createPost, updatePost, deletePost, exportCSV } from "../services/posts"

const ALL_PLATFORMS: Platform[] = ["instagram", "x", "tiktok", "linkedin"]

interface ApiPost {
  id: number
  title: string
  caption: string | null
  platform: string
  scheduled_date: string
  status: string
}

type CalendarPost = Post & { _raw: ApiPost }

function toCalendarPost(p: ApiPost): CalendarPost {
  return {
    id: String(p.id),
    title: p.title,
    platform: p.platform as Platform,
    date: new Date(p.scheduled_date + "T00:00:00"),
    status: p.status as PostStatus,
    _raw: p,
  }
}

function getMonthStr(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`
}

export function DashboardPage() {
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [posts, setPosts] = useState<CalendarPost[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activePlatforms, setActivePlatforms] = useState<Platform[]>(ALL_PLATFORMS)
  const [modalOpen, setModalOpen] = useState(false)
  const [modalMode, setModalMode] = useState<"create" | "edit">("create")
  const [selectedDate, setSelectedDate] = useState<Date | undefined>()
  const [selectedPost, setSelectedPost] = useState<PostData | undefined>()

  const isMobile = useMediaQuery("(max-width: 767px)")
  const userEmail = localStorage.getItem("email") || ""

  const fetchPosts = useCallback(async () => {
    setIsLoading(true)
    try {
      const month = getMonthStr(currentMonth)
      const data = await getPosts(month)
      setPosts((data || []).map(toCalendarPost))
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load posts")
    } finally {
      setIsLoading(false)
    }
  }, [currentMonth])

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
    })
    setModalMode("edit")
    setModalOpen(true)
  }

  const handleSave = async (postData: PostData) => {
    try {
      const body = {
        title: postData.title,
        caption: postData.caption,
        platform: postData.platform,
        scheduled_date: postData.scheduledDate.toISOString().split("T")[0],
        status: postData.status,
      }
      if (modalMode === "create") {
        await createPost(body)
      } else if (postData.id) {
        await updatePost(postData.id, body)
      }
      await fetchPosts()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save post")
    }
  }

  const handleDelete = async (postId: string) => {
    try {
      await deletePost(postId)
      await fetchPosts()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to delete post")
    }
  }

  const handleLogout = () => {
    localStorage.removeItem("token")
    localStorage.removeItem("email")
    window.location.href = "/login"
  }

  const handleToday = () => {
    setCurrentMonth(new Date())
  }

  const handlePlatformToggle = (platform: Platform) => {
    setActivePlatforms((prev) =>
      prev.includes(platform)
        ? prev.filter((p) => p !== platform)
        : [...prev, platform]
    )
  }

  const handleMarkPublished = async (post: MobilePost) => {
    try {
      await updatePost(post.id, { status: "published" })
      await fetchPosts()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to update status")
    }
  }

  const handleExport = async () => {
    try {
      await exportCSV(getMonthStr(currentMonth))
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Export failed")
    }
  }

  const filteredPosts = posts.filter((p) => activePlatforms.includes(p.platform))

  return (
    <div style={{ backgroundColor: "#0F0F0F", minHeight: "100vh" }}>
      <CalendoNavbar
        userEmail={userEmail}
        currentMonth={currentMonth}
        onLogout={handleLogout}
        onTodayClick={handleToday}
      />

      <main className="mx-auto max-w-[1400px] px-4 pb-8 pt-16 md:px-6">
        {!isMobile && (
          <div className="mb-4 flex items-center justify-between">
            <PlatformFilter
              activePlatforms={activePlatforms}
              onToggle={handlePlatformToggle}
            />
            <ExportButton onExport={handleExport} />
          </div>
        )}

        {isLoading ? (
          <LoadingSkeleton />
        ) : isMobile ? (
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

      {error && <ErrorToast message={error} onClose={() => setError(null)} />}
    </div>
  )
}
