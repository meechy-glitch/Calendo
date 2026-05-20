"use client"
import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Calendar, Smartphone, Users, PlusCircle, CheckCircle } from "lucide-react"
import { demoApi } from "@/services/auth"

const platforms = [
  { name: "Instagram", color: "#833AB4" },
  { name: "X", color: "#888888" },
  { name: "TikTok", color: "#FE2C55" },
  { name: "LinkedIn", color: "#0A66C2" },
]

// May 2026 starts on Friday (index 5, 0=Sun)
const calendarCells: (number | null)[] = [
  ...Array(5).fill(null),
  ...Array.from({ length: 31 }, (_, i) => i + 1),
]
while (calendarCells.length % 7 !== 0) calendarCells.push(null)

const mockChips: Record<number, { color: string; label: string }> = {
  3:  { color: "#833AB4", label: "Product drop" },
  7:  { color: "#FE2C55", label: "BTS clip" },
  12: { color: "#888888", label: "Thread" },
  15: { color: "#0A66C2", label: "Team update" },
  19: { color: "#833AB4", label: "Story series" },
  23: { color: "#FE2C55", label: "Tutorial" },
}

function DashboardMockup() {
  const weeks: (number | null)[][] = []
  for (let i = 0; i < calendarCells.length; i += 7) {
    weeks.push(calendarCells.slice(i, i + 7))
  }

  return (
    <div style={{
      transform: "rotate(-2deg)",
      background: "#0A0A0A",
      border: "1px solid #2A2A2A",
      borderRadius: "20px",
      overflow: "hidden",
      boxShadow: "0 24px 64px rgba(0,0,0,0.7), 0 0 0 1px rgba(255,255,255,0.03)",
      width: "100%",
      maxWidth: "340px",
    }}>
      {/* Navbar */}
      <div style={{ padding: "10px 14px", borderBottom: "1px solid #181818", display: "flex", alignItems: "center" }}>
        <span style={{ fontFamily: "var(--font-syne), sans-serif", fontWeight: 800, color: "#E1306C", fontSize: "13px", letterSpacing: "-0.04em" }}>
          Calendo
        </span>
        <div style={{ display: "flex", gap: "4px", marginLeft: "auto" }}>
          {platforms.map(p => (
            <span key={p.name} style={{ width: "5px", height: "5px", borderRadius: "50%", background: p.color, display: "inline-block" }} />
          ))}
        </div>
      </div>

      {/* Month header */}
      <div style={{ padding: "10px 14px 4px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: "11px", fontWeight: 600, color: "#E0E0E0", letterSpacing: "-0.01em" }}>May 2026</span>
        <div style={{ display: "flex", gap: "6px" }}>
          <span style={{ fontSize: "11px", color: "#444" }}>‹</span>
          <span style={{ fontSize: "11px", color: "#444" }}>›</span>
        </div>
      </div>

      {/* Day labels */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", padding: "0 10px" }}>
        {["S","M","T","W","T","F","S"].map((d, i) => (
          <div key={i} style={{ textAlign: "center", fontSize: "8px", color: "#3A3A3A", padding: "1px 0", fontWeight: 600, letterSpacing: "0.05em" }}>{d}</div>
        ))}
      </div>

      {/* Calendar rows */}
      <div style={{ padding: "2px 10px 12px" }}>
        {weeks.map((week, wi) => (
          <div key={wi} style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: "2px", marginBottom: "2px" }}>
            {week.map((day, di) => {
              const chip = day ? mockChips[day] : undefined
              const isToday = day === 19
              return (
                <div key={di} style={{
                  minHeight: chip ? "34px" : "26px",
                  padding: "2px",
                  borderRadius: "3px",
                  background: isToday ? "rgba(225,48,108,0.07)" : "transparent",
                }}>
                  {day && (
                    <span style={{
                      display: "block",
                      textAlign: "center",
                      fontSize: "8px",
                      color: isToday ? "#E1306C" : "#4A4A4A",
                      fontWeight: isToday ? 700 : 400,
                      lineHeight: "11px",
                      marginBottom: chip ? "2px" : "0",
                    }}>
                      {day}
                    </span>
                  )}
                  {chip && (
                    <div style={{
                      background: chip.color + "1A",
                      borderLeft: `1.5px solid ${chip.color}`,
                      borderRadius: "2px",
                      padding: "1px 2px",
                      fontSize: "5.5px",
                      color: chip.color,
                      fontWeight: 600,
                      lineHeight: 1.3,
                      overflow: "hidden",
                      whiteSpace: "nowrap",
                      textOverflow: "ellipsis",
                    }}>
                      {chip.label}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}

export default function LandingPage() {
  const router = useRouter()
  const [ready, setReady] = useState(false)
  const [isDemoLoading, setIsDemoLoading] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem("token")
    if (token) {
      router.replace("/dashboard")
    } else {
      setReady(true)
    }
  }, [router])

  const handleDemo = async () => {
    setIsDemoLoading(true)
    try {
      const data = await demoApi()
      localStorage.setItem("token", data.access_token)
      localStorage.setItem("email", "demo@calendo.app")
      router.push("/dashboard")
    } catch {
      setIsDemoLoading(false)
    }
  }

  if (!ready) return null

  return (
    <>
      <style>{`
        .lp-cta-primary {
          display: flex; align-items: center; justify-content: center;
          padding: 14px 28px; background: #E1306C; color: #F5F5F5;
          border-radius: 10px; font-size: 15px; font-weight: 700;
          text-decoration: none; letter-spacing: -0.01em; transition: opacity 0.15s;
        }
        .lp-cta-primary:hover { opacity: 0.82; }
        .lp-signin-link { color: #E1306C; text-decoration: none; transition: text-decoration 0.1s; }
        .lp-signin-link:hover { text-decoration: underline; text-underline-offset: 2px; }
        .lp-pill {
          display: inline-flex; align-items: center; gap: 5px;
          padding: 0.25rem 0.75rem; border-radius: 999px;
          border: 1px solid rgba(255,255,255,0.07);
          background: rgba(255,255,255,0.025);
          font-size: 0.75rem; font-weight: 500; color: #707070; letter-spacing: 0.01em;
          white-space: nowrap; flex-shrink: 0;
        }
        .lp-pills-row { scrollbar-width: none; -ms-overflow-style: none; }
        .lp-pills-row::-webkit-scrollbar { display: none; }
        .lp-cta-demo {
          display: flex; align-items: center; justify-content: center;
          padding: 14px 28px; background: transparent; color: #888888;
          border: 1px solid #2A2A2A; border-radius: 10px;
          font-size: 15px; font-weight: 600; cursor: pointer;
          letter-spacing: -0.01em; transition: color 0.15s, border-color 0.15s;
          text-align: center;
        }
        .lp-cta-demo:hover:not(:disabled) { color: #E1306C; border-color: #E1306C; }
        .lp-cta-demo:disabled { opacity: 0.5; cursor: default; }
      `}</style>

      <div style={{ backgroundColor: "#0F0F0F", minHeight: "100vh", color: "#F5F5F5" }}>

        {/* Hero */}
        <section style={{ maxWidth: "960px", margin: "0 auto", padding: "56px 24px 52px" }}>
          <div className="grid md:grid-cols-2 md:gap-16 items-center">

            {/* Left: Copy + CTAs */}
            <div className="flex flex-col items-center text-center md:items-start md:text-left">
              <h1
                className="text-5xl md:text-7xl mb-3"
                style={{
                  fontFamily: "var(--font-syne), sans-serif",
                  fontWeight: 800,
                  letterSpacing: "-0.045em",
                  color: "#E1306C",
                  lineHeight: 1,
                }}
              >
                Calendo
              </h1>

              <p className="mb-2" style={{ fontSize: "clamp(16px, 2.8vw, 20px)", color: "#AAAAAA", fontWeight: 300, lineHeight: 1.4, letterSpacing: "-0.01em" }}>
                Stop planning in DMs.
              </p>

              <p className="mb-5" style={{ fontSize: "13px", color: "#888888", fontWeight: 400, lineHeight: 1.5, maxWidth: "300px" }}>
                Built for social media teams that need to stay organized.
              </p>

              {/* Platform pills — scrollable on mobile */}
              <div className="relative w-full mb-5 md:mb-6">
                <div
                  className="lp-pills-row flex flex-nowrap gap-2 overflow-x-auto"
                  style={{ scrollbarWidth: "none", msOverflowStyle: "none" } as React.CSSProperties}
                >
                  {platforms.map((p) => (
                    <span key={p.name} className="lp-pill">
                      <span style={{ width: "6px", height: "6px", borderRadius: "50%", backgroundColor: p.color, flexShrink: 0 }} />
                      {p.name}
                    </span>
                  ))}
                </div>
                {/* Right fade — hints scrollability on mobile */}
                <div
                  className="md:hidden absolute right-0 top-0 bottom-0 w-10 pointer-events-none"
                  style={{ background: "linear-gradient(to right, transparent, #0F0F0F)" }}
                />
              </div>

              {/* CTAs */}
              <div className="flex flex-col items-center text-center gap-3 w-full md:w-auto md:items-start md:text-left">
                <Link href="/register" className="lp-cta-primary w-full md:w-auto">
                  Get Started
                </Link>
                <button
                  onClick={handleDemo}
                  disabled={isDemoLoading}
                  className="lp-cta-demo w-full md:w-auto"
                >
                  {isDemoLoading ? "Loading..." : "Try Demo"}
                </button>
                <p style={{ fontSize: "13px", color: "#666666", margin: 0 }}>
                  Already have an account?{" "}
                  <Link href="/login" className="lp-signin-link">Sign in</Link>
                </p>
              </div>
            </div>

            {/* Right: Dashboard mockup — below CTAs on mobile, beside on desktop */}
            <div
              className="flex justify-center mt-12 md:mt-0 md:justify-end"
              style={{ overflowX: "clip" }}
            >
              <DashboardMockup />
            </div>

          </div>
        </section>

        {/* Feature cards */}
        <section style={{ maxWidth: "900px", margin: "0 auto", padding: "0 20px 72px" }}>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
            <div
              className="col-span-2 md:col-span-1"
              style={{
                borderRadius: "14px",
                border: "1px solid #2A1520",
                borderLeft: "2px solid #E1306C",
                background: "#130D10",
                padding: "28px 24px",
              }}
            >
              <Calendar size={20} style={{ color: "#E1306C", marginBottom: "14px", display: "block" }} />
              <h3 style={{ fontSize: "15px", fontWeight: 600, color: "#F0F0F0", margin: "0 0 7px", letterSpacing: "-0.01em" }}>
                Schedule across 4 platforms
              </h3>
              <p style={{ fontSize: "13px", lineHeight: 1.65, color: "#565656", margin: 0 }}>
                Instagram, X, TikTok and LinkedIn. One calendar.
              </p>
            </div>

            <div style={{ borderRadius: "14px", border: "1px solid #242424", background: "#141414", padding: "28px 24px" }}>
              <Smartphone size={20} style={{ color: "#555555", marginBottom: "14px", display: "block" }} />
              <h3 style={{ fontSize: "15px", fontWeight: 600, color: "#F0F0F0", margin: "0 0 7px", letterSpacing: "-0.01em" }}>
                Publish from your phone
              </h3>
              <p style={{ fontSize: "13px", lineHeight: 1.65, color: "#565656", margin: 0 }}>
                Tap to create, mark as published, manage on the go.
              </p>
            </div>

            <div style={{ borderRadius: "14px", border: "1px solid #242424", background: "#141414", padding: "28px 24px" }}>
              <Users size={20} style={{ color: "#555555", marginBottom: "14px", display: "block" }} />
              <h3 style={{ fontSize: "15px", fontWeight: 600, color: "#F0F0F0", margin: "0 0 7px", letterSpacing: "-0.01em" }}>
                Track everything in one place
              </h3>
              <p style={{ fontSize: "13px", lineHeight: 1.65, color: "#565656", margin: 0 }}>
                Draft, Scheduled, Published. Always know what&apos;s going out.
              </p>
            </div>
          </div>
        </section>

        {/* How it works */}
        <section style={{ maxWidth: "900px", margin: "0 auto", padding: "0 20px 80px" }}>
          <h2 style={{ fontSize: "22px", fontWeight: 700, color: "#F5F5F5", letterSpacing: "-0.02em", marginBottom: "36px", textAlign: "center" }}>
            How it works
          </h2>
          <div className="flex flex-col md:flex-row md:items-start gap-8 md:gap-0">

            <div className="flex-1 flex flex-col items-center text-center md:items-start md:text-left">
              <span style={{ fontSize: "11px", fontWeight: 700, color: "#E1306C", letterSpacing: "0.08em", marginBottom: "6px" }}>01</span>
              <PlusCircle size={20} style={{ color: "#E1306C", marginBottom: "8px" }} />
              <h3 style={{ fontSize: "15px", fontWeight: 600, color: "#F0F0F0", margin: "0 0 4px", letterSpacing: "-0.01em" }}>Add your content</h3>
              <p style={{ fontSize: "13px", color: "#565656", lineHeight: 1.6, margin: 0, maxWidth: "200px" }}>
                Create posts with captions, platform, date and time.
              </p>
            </div>

            {/* Connector — desktop only */}
            <div className="hidden md:flex items-start" style={{ width: "60px", flexShrink: 0, paddingTop: "49px" }}>
              <div style={{ width: "100%", borderTop: "1px dashed #2A2A2A" }} />
            </div>

            <div className="flex-1 flex flex-col items-center text-center md:items-start md:text-left">
              <span style={{ fontSize: "11px", fontWeight: 700, color: "#E1306C", letterSpacing: "0.08em", marginBottom: "6px" }}>02</span>
              <Calendar size={20} style={{ color: "#E1306C", marginBottom: "8px" }} />
              <h3 style={{ fontSize: "15px", fontWeight: 600, color: "#F0F0F0", margin: "0 0 4px", letterSpacing: "-0.01em" }}>Schedule across platforms</h3>
              <p style={{ fontSize: "13px", color: "#565656", lineHeight: 1.6, margin: 0, maxWidth: "200px" }}>
                See everything on one calendar. Filter by platform, export your plan.
              </p>
            </div>

            {/* Connector — desktop only */}
            <div className="hidden md:flex items-start" style={{ width: "60px", flexShrink: 0, paddingTop: "49px" }}>
              <div style={{ width: "100%", borderTop: "1px dashed #2A2A2A" }} />
            </div>

            <div className="flex-1 flex flex-col items-center text-center md:items-start md:text-left">
              <span style={{ fontSize: "11px", fontWeight: 700, color: "#E1306C", letterSpacing: "0.08em", marginBottom: "6px" }}>03</span>
              <CheckCircle size={20} style={{ color: "#E1306C", marginBottom: "8px" }} />
              <h3 style={{ fontSize: "15px", fontWeight: 600, color: "#F0F0F0", margin: "0 0 4px", letterSpacing: "-0.01em" }}>Track what&apos;s published</h3>
              <p style={{ fontSize: "13px", color: "#565656", lineHeight: 1.6, margin: 0, maxWidth: "200px" }}>
                Mark posts as published. Daily summary shows what&apos;s going out today.
              </p>
            </div>

          </div>
        </section>

        {/* Footer */}
        <footer style={{ borderTop: "1px solid #181818", padding: "24px", textAlign: "center" }}>
          <p style={{ fontSize: "11px", color: "#3C3C3C", margin: 0, letterSpacing: "0.03em" }}>
            Made for brands that actually post.{" "}
            <span style={{ color: "#484848" }}>Built by Credible Studios.</span>
          </p>
        </footer>

      </div>
    </>
  )
}
