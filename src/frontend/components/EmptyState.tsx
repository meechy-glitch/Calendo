"use client"
export function EmptyState() {
  return (
    <div className="flex min-h-[400px] flex-col items-center justify-center rounded-lg border border-[#2A2A2A] bg-[#1A1A1A] p-8">
      <svg
        className="mb-6 h-20 w-20"
        viewBox="0 0 64 64"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        {/* Calendar body */}
        <rect x="4" y="10" width="56" height="50" rx="4" stroke="#2A2A2A" strokeWidth="2" />
        {/* Header bar */}
        <rect x="4" y="10" width="56" height="16" rx="4" fill="#2A2A2A" />
        <rect x="4" y="18" width="56" height="8" fill="#2A2A2A" />
        {/* Calendar pegs */}
        <line x1="20" y1="6" x2="20" y2="16" stroke="#555555" strokeWidth="2.5" strokeLinecap="round" />
        <line x1="44" y1="6" x2="44" y2="16" stroke="#555555" strokeWidth="2.5" strokeLinecap="round" />
        {/* Grid dots — row 1 */}
        <circle cx="14" cy="34" r="2.5" fill="#333333" />
        <circle cx="23" cy="34" r="2.5" fill="#333333" />
        <circle cx="32" cy="34" r="2.5" fill="#E1306C" className="animate-pulse" />
        <circle cx="41" cy="34" r="2.5" fill="#333333" />
        <circle cx="50" cy="34" r="2.5" fill="#333333" />
        {/* Grid dots — row 2 */}
        <circle cx="14" cy="44" r="2.5" fill="#333333" />
        <circle cx="23" cy="44" r="2.5" fill="#333333" />
        <circle cx="32" cy="44" r="2.5" fill="#333333" />
        <circle cx="41" cy="44" r="2.5" fill="#333333" />
        <circle cx="50" cy="44" r="2.5" fill="#333333" />
        {/* Grid dots — row 3 */}
        <circle cx="14" cy="54" r="2.5" fill="#333333" />
        <circle cx="23" cy="54" r="2.5" fill="#333333" />
        <circle cx="32" cy="54" r="2.5" fill="#333333" />
        <circle cx="41" cy="54" r="2.5" fill="#333333" />
      </svg>
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
