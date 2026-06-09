"use client"
import { useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import { AppShell, type AppTab } from "@/components/AppShell"
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
import { ChatPanel } from "@/components/ChatPanel"
import { BrandVoiceSettings } from "@/components/BrandVoiceSettings"
import { ReadyQueue } from "@/components/ReadyQueue"
import { NotificationSettings } from "@/components/NotificationSettings"

const ALL_PLATFORMS: Platform[] = ["instagram", "x", "tiktok", "linkedin"]

interface ApiMediaAsset {
  id: number
  public_url: string | null
  thumbnail_key: string | null
  mime_type: string | null
  storage_key: string
  file_size_bytes: number | null
  width: number | null
  height: number | null
  duration_seconds: number | null
  status: string
  created_at: string
  spec_warnings: Record<string, string[]> | null
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
  media_assets: ApiMediaAsset[]
}

type CalendarPost = Post & { _raw: ApiPost }

function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  )
}

function _thumbUrl(asset: ApiMediaAsset): string | undefined {
  if (!asset.public_url) return undefined
  if (asset.thumbnail_key) {
    const base = asset.public_url.split("/users/")[0]
    return `${base}/${asset.thumbnail_key}`
  }
  return asset.public_url
}

function toCalendarPost(p: ApiPost): CalendarPost {
  const firstAsset = p.media_assets?.[0]
  return {
    id: String(p.id),
    title: p.title,
    platform: p.platform as Platform,
    date: new Date(p.scheduled_date + "T00:00:00"),
    status: p.status as PostStatus,
    scheduledTime: p.scheduled_time || undefined,
    mediaUrl: firstAsset ? _thumbUrl(firstAsset) : undefined,
    isVideo: firstAsset?.mime_type?.startsWith("video/") ?? false,
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
  const [activeTab, setActiveTab] = useState<AppTab>("today")
  const [currentMonth, setCurrentMonth] = useState(new Date())
  const [posts, setPosts] = useState<CalendarPost[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null)
  const [activePlatforms, setActivePlatforms] = useState<Platform[]>(ALL_PLATFORMS)
  const [modalOpen, setModalOpen] = useState(false)
  const [modalMode, setModalMode] = useState<"create" | "edit">("create")
  const [selectedDate, setSelectedDate] = useState<Date | undefined>()
  const [selectedPost, setSelectedPost] = useState<PostData | undefined>()
  const [brandVoiceOpen, setBrandVoiceOpen] = useState(false)
  const [notifSettingsOpen, setNotifSettingsOpen] = useState(false)
  const [readyCount, setReadyCount] = useState(0)
  const [readyRefreshKey, setReadyRefreshKey] = useState(0)
  const [demoBannerDismissed, setDemoBannerDismissed] = useState(false)

  const isMobile = useMediaQuery("(max-width: 767px)")
  const userEmail = typeof window !== "undefined" ? localStorage.getItem("email") || "" : ""
  const isDemo = userEmail === "demo@calendo.app"

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
      setReadyRefreshKey((k) => k + 1)
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Failed to load posts", "error")
    } finally {
      setIsLoading(false)
    }
  }, [currentMonth, showToast])

  useEffect(() => {
    fetchPosts()
  }, [fetchPosts])

  // Fetch posts when switching to calendar tab
  useEffect(() => {
    if (activeTab === "calendar") fetchPosts()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab])

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
      mediaItems: (raw.media_assets || []).map((a) => ({
        asset: {
          id: a.id,
          storage_key: a.storage_key,
          public_url: a.public_url,
          original_filename: null,
          mime_type: a.mime_type,
          file_size_bytes: a.file_size_bytes,
          width: a.width,
          height: a.height,
          duration_seconds: a.duration_seconds,
          thumbnail_key: a.thumbnail_key,
          status: a.status,
          created_at: a.created_at,
          spec_warnings: a.spec_warnings,
        },
        localUrl: _thumbUrl(a) || "",
      })),
    })
    setModalMode("edit")
    setModalOpen(true)
  }

  const handleSave = async (postData: PostData) => {
    const mediaIds = postData.mediaItems?.map((m) => m.asset.id) ?? null
    const baseBody = {
      title: postData.title,
      caption: postData.caption,
      scheduled_date: toLocalDateString(postData.scheduledDate),
      status: postData.status,
      scheduled_time: postData.scheduledTime || null,
      notes: postData.notes || null,
      media_ids: mediaIds,
    }

    if (modalMode === "create") {
      const platforms = postData.platforms && postData.platforms.length > 0
        ? postData.platforms
        : [postData.platform]

      if (platforms.length > 1) {
        setIsLoading(true)
        try {
          await Promise.all(platforms.map((p) => createPost({ ...baseBody, platform: p })))
          showToast(`${platforms.length} posts scheduled ✓`, "success")
          await fetchPosts()
        } catch (err: unknown) {
          showToast(err instanceof Error ? err.message : "Failed to save posts", "error")
          setIsLoading(false)
        }
        return
      }

      const body = { ...baseBody, platform: postData.platform }
      const tempId = `temp-${Date.now()}`
      const tempRaw: ApiPost = {
        id: 0, title: postData.title, caption: postData.caption || null,
        platform: postData.platform,
        scheduled_date: toLocalDateString(postData.scheduledDate),
        status: postData.status, scheduled_time: postData.scheduledTime || null,
        notes: postData.notes || null,
        media_assets: (postData.mediaItems || []).map((m) => ({
          id: m.asset.id, public_url: m.asset.public_url, thumbnail_key: m.asset.thumbnail_key,
          mime_type: m.asset.mime_type, storage_key: m.asset.storage_key,
          file_size_bytes: m.asset.file_size_bytes, width: m.asset.width, height: m.asset.height,
          duration_seconds: m.asset.duration_seconds, status: m.asset.status,
          created_at: m.asset.created_at, spec_warnings: m.asset.spec_warnings,
        })),
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
      const body = { ...baseBody, platform: postData.platform }
      const originalPost = posts.find((p) => p.id === postData.id)
      const tempRaw: ApiPost = {
        id: parseInt(postData.id), title: postData.title, caption: postData.caption || null,
        platform: postData.platform,
        scheduled_date: toLocalDateString(postData.scheduledDate),
        status: postData.status, scheduled_time: postData.scheduledTime || null,
        notes: postData.notes || null,
        media_assets: (postData.mediaItems || []).map((m) => ({
          id: m.asset.id, public_url: m.asset.public_url, thumbnail_key: m.asset.thumbnail_key,
          mime_type: m.asset.mime_type, storage_key: m.asset.storage_key,
          file_size_bytes: m.asset.file_size_bytes, width: m.asset.width, height: m.asset.height,
          duration_seconds: m.asset.duration_seconds, status: m.asset.status,
          created_at: m.asset.created_at, spec_warnings: m.asset.spec_warnings,
        })),
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

  return (
    <AppShell
      activeTab={activeTab}
      onTabChange={setActiveTab}
      readyCount={readyCount}
      userEmail={userEmail}
      onAddPost={() => { setActiveTab("calendar"); handleDateClick(new Date()) }}
    >
      {/* Today tab */}
      {activeTab === "today" && (
        <div className="mx-auto max-w-[800px] px-4 py-6 md:px-6">
          <ReadyQueue refreshKey={readyRefreshKey} onCountChange={setReadyCount} />
          {readyCount === 0 && (
            <div
              className="rounded-lg border p-10 text-center"
              style={{ borderColor: "#2A2A2A" }}
            >
              <p className="text-base font-medium" style={{ color: "#F5F5F5" }}>
                You&apos;re all clear
              </p>
              <p className="mt-1 text-sm" style={{ color: "#888888" }}>
                No posts ready to publish today.
              </p>
              <button
                onClick={() => setActiveTab("calendar")}
                className="mt-4 rounded-lg border px-4 py-2 text-sm font-medium transition-colors hover:border-[#E1306C] hover:text-[#E1306C]"
                style={{ backgroundColor: "transparent", borderColor: "#2A2A2A", color: "#888888" }}
              >
                Open Calendar
              </button>
            </div>
          )}
        </div>
      )}

      {/* Calendar tab */}
      {activeTab === "calendar" && (
        <div className="mx-auto max-w-[1400px] px-4 py-6 md:px-6">
          {isDemo && !demoBannerDismissed && (
            <div
              className="mb-4 flex items-center justify-between rounded-md px-4 py-2.5 text-sm"
              style={{ backgroundColor: "#1A1A1A", border: "1px solid #2A2A2A", color: "#888888" }}
            >
              <span>
                You&apos;re viewing a demo account.{" "}
                <a href="/register" style={{ color: "#888888", textDecoration: "underline", textUnderlineOffset: "3px" }}>
                  Sign up
                </a>
                {" "}to save your own content.
              </span>
              <button
                onClick={() => setDemoBannerDismissed(true)}
                className="ml-4 flex-shrink-0 leading-none hover:text-[#F5F5F5]"
                aria-label="Dismiss"
                style={{ color: "#555555", fontSize: "18px" }}
              >
                ×
              </button>
            </div>
          )}

          <AnalyticsSummary posts={filteredPosts} />

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
              {isMobile ? (
                <>
                  <CalendarMobile
                    posts={filteredPosts}
                    currentMonth={currentMonth}
                    onDateClick={handleDateClick}
                    onPostClick={handlePostClick}
                    onMonthChange={setCurrentMonth}
                    onMarkPublished={handleMarkPublished}
                  />
                  <div
                    className="mt-8 border-t pt-4 text-center"
                    style={{ borderColor: "#1E1E1E" }}
                  >
                    <FeedbackButton variant="link" onSubmit={() => {}} />
                  </div>
                </>
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
        </div>
      )}

      {/* Assistant tab */}
      {activeTab === "assistant" && (
        <div className="h-[calc(100vh-120px)] md:h-[calc(100vh-56px)]">
          <ChatPanel onClose={() => setActiveTab("today")} onChanges={fetchPosts} embedded />
        </div>
      )}

      {/* Settings tab */}
      {activeTab === "settings" && (
        <div className="mx-auto max-w-[640px] space-y-4 px-4 py-8 md:px-6">
          <h1 className="text-lg font-semibold" style={{ color: "#F5F5F5" }}>Settings</h1>

          <div
            className="rounded-lg border p-4"
            style={{ backgroundColor: "#1A1A1A", borderColor: "#2A2A2A" }}
          >
            <p className="mb-0.5 text-sm font-medium" style={{ color: "#F5F5F5" }}>Brand Voice</p>
            <p className="mb-3 text-xs" style={{ color: "#888888" }}>
              Configure the tone and style for AI-generated captions.
            </p>
            <button
              onClick={() => setBrandVoiceOpen(true)}
              className="rounded-lg border px-4 py-2 text-sm font-medium transition-colors hover:border-[#E1306C] hover:text-[#E1306C]"
              style={{ backgroundColor: "transparent", borderColor: "#2A2A2A", color: "#888888" }}
            >
              Edit Brand Voice
            </button>
          </div>

          <div
            className="rounded-lg border p-4"
            style={{ backgroundColor: "#1A1A1A", borderColor: "#2A2A2A" }}
          >
            <p className="mb-0.5 text-sm font-medium" style={{ color: "#F5F5F5" }}>Notifications</p>
            <p className="mb-3 text-xs" style={{ color: "#888888" }}>
              Configure lead-time reminders for scheduled posts.
            </p>
            <button
              onClick={() => setNotifSettingsOpen(true)}
              className="rounded-lg border px-4 py-2 text-sm font-medium transition-colors hover:border-[#E1306C] hover:text-[#E1306C]"
              style={{ backgroundColor: "transparent", borderColor: "#2A2A2A", color: "#888888" }}
            >
              Notification Preferences
            </button>
          </div>

          <div
            className="rounded-lg border p-4"
            style={{ backgroundColor: "#1A1A1A", borderColor: "#2A2A2A" }}
          >
            <p className="mb-0.5 text-sm font-medium" style={{ color: "#F5F5F5" }}>Feedback</p>
            <p className="mb-3 text-xs" style={{ color: "#888888" }}>
              Share your thoughts to help improve Calendo.
            </p>
            <FeedbackButton onSubmit={() => {}} />
          </div>

          <div className="pt-2">
            <button
              onClick={handleLogout}
              className="rounded-lg border px-4 py-2 text-sm font-medium transition-colors hover:border-red-700 hover:text-red-400"
              style={{ backgroundColor: "transparent", borderColor: "#2A2A2A", color: "#888888" }}
            >
              Log out
            </button>
          </div>
        </div>
      )}

      {/* Portals — always mounted */}
      <PostModal
        isOpen={modalOpen}
        mode={modalMode}
        post={selectedPost}
        scheduledDate={selectedDate}
        onSave={handleSave}
        onDelete={modalMode === "edit" ? handleDelete : undefined}
        onClose={() => setModalOpen(false)}
      />
      <BrandVoiceSettings isOpen={brandVoiceOpen} onClose={() => setBrandVoiceOpen(false)} />
      <NotificationSettings isOpen={notifSettingsOpen} onClose={() => setNotifSettingsOpen(false)} />
      {toast && <Toast message={toast.message} type={toast.type} onClose={hideToast} />}
    </AppShell>
  )
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  )
}
