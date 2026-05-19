"use client"
import { Button } from "@/components/ui/button"

interface CalendoNavbarProps {
  userEmail: string
  currentMonth: Date
  onLogout: () => void
  onTodayClick: () => void
}

export function CalendoNavbar({ userEmail, currentMonth, onLogout, onTodayClick }: CalendoNavbarProps) {
  const monthYearDisplay = currentMonth.toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
  })

  return (
    <nav
      className="fixed top-0 right-0 left-0 z-50 flex h-14 items-center justify-between border-b px-4 md:px-6"
      style={{ backgroundColor: "#0F0F0F", borderColor: "#2A2A2A" }}
    >
      <div className="flex min-w-0 flex-1 items-center gap-4">
        <span className="text-xl font-bold tracking-tight" style={{ color: "#E1306C" }}>Calendo</span>
        <Button
          variant="outline"
          size="sm"
          onClick={onTodayClick}
          className="h-7 border px-2.5 text-xs transition-colors hover:border-[#E1306C] hover:text-[#E1306C]"
          style={{ backgroundColor: "transparent", borderColor: "#2A2A2A", color: "#888888" }}
        >
          Today
        </Button>
      </div>

      <div className="hidden flex-1 justify-center sm:flex">
        <span
          className="rounded-full border px-4 py-1 text-sm font-medium"
          style={{ backgroundColor: "#1A1A1A", borderColor: "#2A2A2A", color: "#F5F5F5" }}
        >
          {monthYearDisplay}
        </span>
      </div>

      <div className="flex min-w-0 flex-1 items-center justify-end gap-3">
        <span
          className="hidden max-w-[180px] truncate text-sm md:block"
          style={{ color: "#888888" }}
          title={userEmail}
        >
          {userEmail}
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={onLogout}
          className="h-8 border px-3 text-xs transition-colors hover:border-[#E1306C] hover:text-[#E1306C]"
          style={{ backgroundColor: "transparent", borderColor: "#2A2A2A", color: "#888888" }}
        >
          Logout
        </Button>
      </div>
    </nav>
  )
}
