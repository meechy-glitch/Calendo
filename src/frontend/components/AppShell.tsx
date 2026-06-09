"use client"
import { Bot, CalendarDays, Home, Plus, Settings } from "lucide-react"

export type AppTab = "today" | "calendar" | "assistant" | "settings"

interface AppShellProps {
  activeTab: AppTab
  onTabChange: (tab: AppTab) => void
  readyCount: number
  userEmail: string
  onAddPost: () => void
  children: React.ReactNode
}

const TABS: { id: AppTab; label: string; Icon: React.ComponentType<{ size?: number }> }[] = [
  { id: "today", label: "Today", Icon: Home },
  { id: "calendar", label: "Calendar", Icon: CalendarDays },
  { id: "assistant", label: "Assistant", Icon: Bot },
  { id: "settings", label: "Settings", Icon: Settings },
]

export function AppShell({ activeTab, onTabChange, readyCount, userEmail, onAddPost, children }: AppShellProps) {
  return (
    <div style={{ backgroundColor: "#0F0F0F", minHeight: "100vh" }}>

      {/* Desktop sidebar */}
      <aside
        className="fixed inset-y-0 left-0 z-30 hidden w-56 flex-col border-r md:flex"
        style={{ backgroundColor: "#0F0F0F", borderColor: "#2A2A2A" }}
      >
        <div
          className="flex h-14 flex-shrink-0 items-center border-b px-5"
          style={{ borderColor: "#2A2A2A" }}
        >
          <span className="text-xl font-bold tracking-tight" style={{ color: "#E1306C" }}>Calendo</span>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto p-3">
          {TABS.map(({ id, label, Icon }) => (
            <button
              key={id}
              onClick={() => onTabChange(id)}
              className="relative flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors hover:bg-[#1A1A1A]"
              style={{
                color: activeTab === id ? "#E1306C" : "#888888",
                backgroundColor: activeTab === id ? "rgba(225,48,108,0.08)" : "transparent",
              }}
            >
              <Icon size={18} />
              {label}
              {id === "today" && readyCount > 0 && (
                <span
                  className="absolute right-3 flex h-4 min-w-[16px] items-center justify-center rounded-full px-1 text-[10px] font-bold"
                  style={{ backgroundColor: "#E1306C", color: "#F5F5F5" }}
                >
                  {readyCount}
                </span>
              )}
            </button>
          ))}
        </nav>

        <div className="flex-shrink-0 border-t p-4" style={{ borderColor: "#2A2A2A" }}>
          <p className="truncate text-xs" style={{ color: "#555555" }} title={userEmail}>{userEmail}</p>
        </div>
      </aside>

      {/* Top header */}
      <header
        className="fixed left-0 right-0 top-0 z-30 flex h-14 items-center justify-between border-b px-4 md:left-56 md:px-6"
        style={{ backgroundColor: "#0F0F0F", borderColor: "#2A2A2A" }}
      >
        <span className="text-xl font-bold tracking-tight md:hidden" style={{ color: "#E1306C" }}>Calendo</span>
        <span className="hidden max-w-xs truncate text-sm md:block" style={{ color: "#888888" }}>
          {userEmail}
        </span>
        <button
          onClick={onAddPost}
          className="flex h-8 w-8 items-center justify-center rounded-lg transition-opacity hover:opacity-90"
          style={{ backgroundColor: "#E1306C", color: "#F5F5F5" }}
          aria-label="New post"
        >
          <Plus size={16} />
        </button>
      </header>

      {/* Content area */}
      <main className="pt-14 pb-16 md:ml-56 md:pb-0">
        {children}
      </main>

      {/* Mobile bottom tab bar */}
      <nav
        className="fixed bottom-0 left-0 right-0 z-30 flex h-16 items-stretch border-t md:hidden"
        style={{ backgroundColor: "#0F0F0F", borderColor: "#2A2A2A" }}
      >
        {TABS.map(({ id, label, Icon }) => (
          <button
            key={id}
            onClick={() => onTabChange(id)}
            className="relative flex flex-1 flex-col items-center justify-center gap-0.5 transition-colors"
            style={{ color: activeTab === id ? "#E1306C" : "#888888" }}
          >
            <Icon size={20} />
            <span className="text-[10px] font-medium">{label}</span>
            {id === "today" && readyCount > 0 && (
              <span
                className="absolute right-[calc(50%-10px)] top-2 flex h-4 min-w-[16px] items-center justify-center rounded-full px-1 text-[10px] font-bold"
                style={{ backgroundColor: "#E1306C", color: "#F5F5F5" }}
              >
                {readyCount > 9 ? "9+" : readyCount}
              </span>
            )}
          </button>
        ))}
      </nav>
    </div>
  )
}
