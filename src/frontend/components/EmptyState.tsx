"use client"
export function EmptyState() {
  return (
    <div className="flex min-h-[400px] flex-col items-center justify-center rounded-lg border border-[#2A2A2A] bg-[#1A1A1A] p-8">
      <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-[#0F0F0F]">
        <svg className="h-8 w-8 text-[#888888]" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
          />
        </svg>
      </div>
      <h3 className="mb-2 text-lg font-semibold text-[#F5F5F5]">No posts scheduled</h3>
      <p className="text-center text-sm text-[#888888]">Click any date to schedule your first post</p>
    </div>
  )
}

function SkeletonCell() {
  return (
    <div className="flex h-24 flex-col rounded-md border border-[#2A2A2A] bg-[#1A1A1A] p-2 md:h-28">
      <div className="mb-2 h-5 w-6 animate-pulse rounded bg-[#2A2A2A]" />
      <div className="flex flex-col gap-1">
        <div className="h-4 w-full animate-pulse rounded bg-[#2A2A2A]" style={{ animationDelay: "0ms" }} />
        <div className="h-4 w-3/4 animate-pulse rounded bg-[#2A2A2A]" style={{ animationDelay: "150ms" }} />
      </div>
    </div>
  )
}

export function LoadingSkeleton() {
  const cells = Array.from({ length: 35 }, (_, i) => i)
  return (
    <div className="rounded-lg border border-[#2A2A2A] bg-[#1A1A1A] p-4">
      <div className="mb-4 grid grid-cols-7 gap-2">
        {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((day) => (
          <div key={day} className="flex h-8 items-center justify-center">
            <div className="h-4 w-8 animate-pulse rounded bg-[#2A2A2A]" />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-7 gap-2">
        {cells.map((index) => <SkeletonCell key={index} />)}
      </div>
    </div>
  )
}
