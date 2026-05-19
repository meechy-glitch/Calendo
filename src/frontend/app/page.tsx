"use client"
import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Calendar, Smartphone, Users } from "lucide-react"

const platforms = [
  { name: "Instagram", color: "#833AB4" },
  { name: "X", color: "#888888" },
  { name: "TikTok", color: "#FE2C55" },
  { name: "LinkedIn", color: "#0A66C2" },
]

export default function LandingPage() {
  const router = useRouter()
  const [ready, setReady] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem("token")
    if (token) {
      router.replace("/dashboard")
    } else {
      setReady(true)
    }
  }, [router])

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
        .lp-signin-link {
          color: #E1306C; text-decoration: none; transition: text-decoration 0.1s;
        }
        .lp-signin-link:hover { text-decoration: underline; text-underline-offset: 2px; }
        .lp-pill {
          display: inline-flex; align-items: center; gap: 6px;
          padding: 4px 11px; border-radius: 999px;
          border: 1px solid rgba(255,255,255,0.07);
          background: rgba(255,255,255,0.025);
          font-size: 11px; font-weight: 500; color: #707070; letter-spacing: 0.01em;
          white-space: nowrap; flex-shrink: 0;
        }
        .lp-pills-row::-webkit-scrollbar { display: none; }
      `}</style>

      <div className="px-5 md:px-0 overflow-x-hidden" style={{ backgroundColor: "#0F0F0F", minHeight: "100vh", color: "#F5F5F5" }}>
        {/* Hero */}
        <section className="flex flex-col items-center px-6 text-center pt-12 pb-8 md:pt-[72px] md:pb-[52px]">
          <h1
            className="text-5xl md:text-8xl mb-4"
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

          <p
            className="mb-4 md:mb-5"
            style={{
              fontSize: "clamp(16px, 2.8vw, 19px)",
              color: "#AAAAAA",
              fontWeight: 300,
              lineHeight: 1.5,
              maxWidth: "340px",
              letterSpacing: "-0.01em",
            }}
          >
            Stop planning in DMs.<br />Start shipping content.
          </p>

          {/* Platform pills — single row, scrollable on mobile */}
          <div className="relative w-full mb-4 md:mb-7">
            <div
              className="lp-pills-row flex flex-nowrap gap-2 overflow-x-auto md:justify-center"
              style={{ scrollbarWidth: "none", msOverflowStyle: "none" } as React.CSSProperties}
            >
              {platforms.map((p) => (
                <span key={p.name} className="lp-pill">
                  <span
                    style={{
                      width: "6px",
                      height: "6px",
                      borderRadius: "50%",
                      backgroundColor: p.color,
                      flexShrink: 0,
                    }}
                  />
                  {p.name}
                </span>
              ))}
            </div>
            {/* Right fade hint — mobile only */}
            <div
              className="md:hidden absolute right-0 top-0 bottom-0 w-10 pointer-events-none"
              style={{ background: "linear-gradient(to right, transparent, #0F0F0F)" }}
            />
          </div>

          {/* CTAs */}
          <div className="flex flex-col items-center gap-3 w-full md:w-auto">
            <Link href="/register" className="lp-cta-primary w-full md:w-auto">
              Get Started
            </Link>
            <p style={{ fontSize: "13px", color: "#666666", margin: 0 }}>
              Already have an account?{" "}
              <Link href="/login" className="lp-signin-link">Sign in</Link>
            </p>
          </div>
        </section>

        {/* Features */}
        <section style={{ maxWidth: "900px", margin: "0 auto", padding: "0 20px 80px" }}>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
            {/* Primary card — full width on mobile, 1/3 on desktop */}
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
                Multi-Platform
              </h3>
              <p style={{ fontSize: "13px", lineHeight: 1.65, color: "#565656", margin: 0 }}>
                Instagram, X, TikTok, and LinkedIn. One calendar.
              </p>
            </div>

            <div style={{ borderRadius: "14px", border: "1px solid #242424", background: "#141414", padding: "28px 24px" }}>
              <Smartphone size={20} style={{ color: "#555555", marginBottom: "14px", display: "block" }} />
              <h3 style={{ fontSize: "15px", fontWeight: 600, color: "#F0F0F0", margin: "0 0 7px", letterSpacing: "-0.01em" }}>
                Mobile First
              </h3>
              <p style={{ fontSize: "13px", lineHeight: 1.65, color: "#565656", margin: 0 }}>
                Plan and track content from your phone.
              </p>
            </div>

            <div style={{ borderRadius: "14px", border: "1px solid #242424", background: "#141414", padding: "28px 24px" }}>
              <Users size={20} style={{ color: "#555555", marginBottom: "14px", display: "block" }} />
              <h3 style={{ fontSize: "15px", fontWeight: 600, color: "#F0F0F0", margin: "0 0 7px", letterSpacing: "-0.01em" }}>
                Team Ready
              </h3>
              <p style={{ fontSize: "13px", lineHeight: 1.65, color: "#565656", margin: 0 }}>
                Built for agencies, brands, and content teams.
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
