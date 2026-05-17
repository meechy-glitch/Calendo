"use client"
const PLATFORM_COLORS = {
  instagram: "#833AB4",
  x: "#888888",
  tiktok: "#FE2C55",
  linkedin: "#0A66C2",
} as const

type Platform = keyof typeof PLATFORM_COLORS
type PostStatus = "draft" | "scheduled" | "published"

interface SummaryPost {
  platform: Platform
  status?: PostStatus
}

interface AnalyticsSummaryProps {
  posts: SummaryPost[]
}

const PLATFORM_LABELS: Record<Platform, string> = {
  instagram: "Instagram",
  x: "X",
  tiktok: "TikTok",
  linkedin: "LinkedIn",
}

export function AnalyticsSummary({ posts }: AnalyticsSummaryProps) {
  const platformCounts = (["instagram", "x", "tiktok", "linkedin"] as Platform[]).map(
    (p) => ({ platform: p, count: posts.filter((post) => post.platform === p).length })
  )

  const published = posts.filter((p) => p.status === "published").length
  const scheduled = posts.filter((p) => p.status === "scheduled").length
  const draft = posts.filter((p) => p.status === "draft").length

  return (
    <div className="mb-6 rounded-lg border border-[#2A2A2A] px-4 py-3" style={{ backgroundColor: "#1A1A1A" }}>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
        {platformCounts.map(({ platform, count }) => (
          <span key={platform} className="flex items-center gap-1.5 text-sm" style={{ color: "#F5F5F5" }}>
            <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: PLATFORM_COLORS[platform] }} />
            {PLATFORM_LABELS[platform]}: {count}
          </span>
        ))}
        <span className="text-sm" style={{ color: "#888888" }}>· Total: {posts.length}</span>
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm" style={{ color: "#888888" }}>
        <span>Published: {published}</span>
        <span>·</span>
        <span>Scheduled: {scheduled}</span>
        <span>·</span>
        <span>Draft: {draft}</span>
      </div>
    </div>
  )
}
