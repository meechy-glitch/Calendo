"use client"
import { cn } from "@/lib/utils"

const PLATFORMS = [
  { key: "instagram", name: "Instagram", color: "#833AB4" },
  { key: "x", name: "X", color: "#888888" },
  { key: "tiktok", name: "TikTok", color: "#FE2C55" },
  { key: "linkedin", name: "LinkedIn", color: "#0A66C2" },
] as const

export type Platform = (typeof PLATFORMS)[number]["key"]

interface PlatformFilterProps {
  activePlatforms: Platform[]
  onToggle: (platform: Platform) => void
}

export function PlatformFilter({ activePlatforms, onToggle }: PlatformFilterProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {PLATFORMS.map((platform) => {
        const isActive = activePlatforms.includes(platform.key)
        return (
          <button
            key={platform.key}
            onClick={() => onToggle(platform.key)}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1 rounded-full border transition-all duration-200 text-xs font-medium",
              isActive ? "bg-[#1A1A1A] text-[#F5F5F5]" : "bg-[#1A1A1A]/50 text-[#888888]"
            )}
            style={{
              borderColor: isActive ? platform.color : "#2A2A2A",
            }}
          >
            <span
              className={cn("w-2 h-2 rounded-full transition-opacity duration-200", isActive ? "opacity-100" : "opacity-40")}
              style={{ backgroundColor: platform.color }}
            />
            <span>{platform.name}</span>
          </button>
        )
      })}
    </div>
  )
}
