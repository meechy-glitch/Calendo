"use client"
const PLATFORM_COLORS = {
  instagram: "#833AB4",
  x: "#888888",
  tiktok: "#FE2C55",
  linkedin: "#0A66C2",
} as const

type Platform = keyof typeof PLATFORM_COLORS
type PostStatus = "draft" | "scheduled" | "published" | "ready" | "posted" | "skipped"

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
  const scheduled = posts.filter((p) => p.status === "scheduled").length
  const draft = posts.filter((p) => p.status === "draft").length
  const total = posts.length

  const platformCounts = (["instagram", "x", "tiktok", "linkedin"] as Platform[])
    .map((p) => ({ platform: p, count: posts.filter((post) => post.platform === p).length }))
    .filter(({ count }) => count > 0)

  return (
    <div className="mb-6 space-y-3">
      {/* 3 stat tiles */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Scheduled", value: scheduled },
          { label: "Drafts", value: draft },
          { label: "This month", value: total },
        ].map(({ label, value }) => (
          <div
            key={label}
            className="rounded-lg border px-4 py-3"
            style={{ backgroundColor: "#1A1A1A", borderColor: "#2A2A2A" }}
          >
            <p className="text-xl font-semibold" style={{ color: "#F5F5F5" }}>{value}</p>
            <p className="text-xs" style={{ color: "#888888" }}>{label}</p>
          </div>
        ))}
      </div>

      {/* Compact platform breakdown — only platforms with posts */}
      {platformCounts.length > 0 && (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 px-1">
          {platformCounts.map(({ platform, count }) => (
            <span key={platform} className="flex items-center gap-1.5 text-xs" style={{ color: "#888888" }}>
              <span
                className="inline-block h-2 w-2 flex-shrink-0 rounded-full"
                style={{ backgroundColor: PLATFORM_COLORS[platform] }}
              />
              {PLATFORM_LABELS[platform]}: {count}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
