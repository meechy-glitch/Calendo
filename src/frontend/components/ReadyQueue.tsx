"use client"
import * as React from "react"
import { Bell } from "lucide-react"
import { getReadyQueue } from "@/services/posts"
import { PostNowModal } from "@/components/PostNowModal"

const PLATFORM_COLORS: Record<string, string> = {
  instagram: "#833AB4",
  x: "#888888",
  tiktok: "#FE2C55",
  linkedin: "#0E8C8C",
  facebook: "#1877F2",
}

const PLATFORM_LABELS: Record<string, string> = {
  instagram: "Instagram",
  x: "X",
  tiktok: "TikTok",
  linkedin: "LinkedIn",
  facebook: "Facebook",
}

interface ReadyPost {
  id: number
  title: string
  platform: string
  scheduled_time: string | null
  scheduled_date: string
  notified_at: string | null
}

interface ReadyQueueProps {
  refreshKey?: number
  onCountChange?: (count: number) => void
}

export function ReadyQueue({ refreshKey, onCountChange }: ReadyQueueProps) {
  const [posts, setPosts] = React.useState<ReadyPost[]>([])
  const [activePostId, setActivePostId] = React.useState<number | null>(null)

  const load = React.useCallback(() => {
    getReadyQueue()
      .then((data: ReadyPost[]) => {
        setPosts(data || [])
        onCountChange?.(data?.length ?? 0)
      })
      .catch(() => {})
  }, [onCountChange])

  React.useEffect(() => {
    load()
  }, [load, refreshKey])

  if (posts.length === 0) return null

  const [hero, ...rest] = posts

  return (
    <>
      <div
        className="mb-6 rounded-lg border p-4"
        style={{ backgroundColor: "#1A1A1A", borderColor: "#2A2A2A" }}
      >
        <div className="mb-4 flex items-center gap-2">
          <Bell size={15} style={{ color: "#F5F5F5" }} />
          <span className="text-sm font-semibold" style={{ color: "#F5F5F5" }}>
            Ready to post
          </span>
          <span
            className="rounded-full px-1.5 py-0.5 text-xs font-medium"
            style={{ backgroundColor: "#2A2A2A", color: "#888888" }}
          >
            {posts.length}
          </span>
        </div>

        {/* Hero post — most urgent */}
        <div
          className="mb-3 flex items-center justify-between rounded-lg px-4 py-3"
          style={{ backgroundColor: "#0F0F0F", border: "1px solid #2A2A2A" }}
        >
          <div className="flex min-w-0 items-center gap-3">
            <span
              className="inline-block h-2.5 w-2.5 flex-shrink-0 rounded-full"
              style={{ backgroundColor: PLATFORM_COLORS[hero.platform] ?? "#888" }}
            />
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold" style={{ color: "#F5F5F5" }}>
                {hero.title}
              </p>
              <p className="text-xs" style={{ color: "#888888" }}>
                {PLATFORM_LABELS[hero.platform] ?? hero.platform}
                {hero.scheduled_time ? ` · ${hero.scheduled_time}` : ""}
              </p>
            </div>
          </div>
          <button
            onClick={() => setActivePostId(hero.id)}
            className="ml-4 flex-shrink-0 rounded-lg px-4 py-1.5 text-sm font-medium transition-opacity hover:opacity-90"
            style={{ backgroundColor: "#E1306C", color: "#F5F5F5" }}
          >
            Post now
          </button>
        </div>

        {/* Remaining posts — neutral */}
        {rest.length > 0 && (
          <div className="space-y-2">
            {rest.map((post) => (
              <div
                key={post.id}
                className="flex items-center justify-between rounded px-3 py-2"
                style={{ backgroundColor: "#0F0F0F", border: "1px solid #2A2A2A" }}
              >
                <div className="flex min-w-0 items-center gap-2">
                  <span
                    className="inline-block h-2 w-2 flex-shrink-0 rounded-full"
                    style={{ backgroundColor: PLATFORM_COLORS[post.platform] ?? "#888" }}
                  />
                  <span className="truncate text-sm font-medium" style={{ color: "#F5F5F5" }}>
                    {post.title}
                  </span>
                  <span className="text-xs" style={{ color: "#888888" }}>
                    {PLATFORM_LABELS[post.platform] ?? post.platform}
                    {post.scheduled_time ? ` · ${post.scheduled_time}` : ""}
                  </span>
                </div>
                <button
                  onClick={() => setActivePostId(post.id)}
                  className="ml-3 flex-shrink-0 rounded px-2.5 py-1 text-xs font-medium transition-colors hover:bg-[#2A2A2A]"
                  style={{
                    backgroundColor: "transparent",
                    border: "1px solid #3A3A3A",
                    color: "#888888",
                  }}
                >
                  Post now
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <PostNowModal
        postId={activePostId}
        onClose={() => setActivePostId(null)}
        onDone={() => {
          setActivePostId(null)
          load()
        }}
      />
    </>
  )
}
