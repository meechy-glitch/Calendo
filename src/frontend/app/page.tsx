"use client"
import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Calendar, Smartphone, Users } from "lucide-react"

const features = [
  {
    icon: Calendar,
    title: "Multi-Platform",
    description: "Plan Instagram, X, TikTok and LinkedIn in one place",
  },
  {
    icon: Smartphone,
    title: "Mobile First",
    description: "Manage your content calendar from anywhere",
  },
  {
    icon: Users,
    title: "Team Ready",
    description: "Built for agencies, brands and content teams",
  },
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
    <div style={{ backgroundColor: "#0F0F0F", minHeight: "100vh", color: "#F5F5F5" }}>
      {/* Hero */}
      <section className="flex flex-col items-center justify-center px-4 py-28 text-center">
        <h1 className="mb-4 text-6xl font-bold tracking-tight" style={{ color: "#E1306C" }}>
          Calendo
        </h1>
        <p className="mb-10 max-w-md text-lg leading-relaxed" style={{ color: "#888888" }}>
          The content calendar built for creative teams
        </p>
        <div className="flex flex-wrap justify-center gap-4">
          <Link
            href="/register"
            className="rounded-lg px-6 py-3 text-sm font-semibold transition-opacity hover:opacity-90"
            style={{ backgroundColor: "#E1306C", color: "#F5F5F5" }}
          >
            Get Started
          </Link>
          <Link
            href="/login"
            className="rounded-lg border px-6 py-3 text-sm font-semibold transition-colors hover:border-[#E1306C] hover:text-[#E1306C]"
            style={{ borderColor: "#2A2A2A", color: "#F5F5F5" }}
          >
            Sign In
          </Link>
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-4xl px-4 pb-28">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="rounded-xl border p-6"
              style={{ backgroundColor: "#1A1A1A", borderColor: "#2A2A2A" }}
            >
              <feature.icon className="mb-4 h-6 w-6" style={{ color: "#E1306C" }} />
              <h3 className="mb-2 font-semibold" style={{ color: "#F5F5F5" }}>
                {feature.title}
              </h3>
              <p className="text-sm leading-relaxed" style={{ color: "#888888" }}>
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-8 text-center" style={{ borderColor: "#2A2A2A" }}>
        <p className="text-sm" style={{ color: "#555555" }}>
          Built by Credible Studios
        </p>
      </footer>
    </div>
  )
}
