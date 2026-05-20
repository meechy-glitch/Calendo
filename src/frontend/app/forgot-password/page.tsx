"use client"
import * as React from "react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Spinner } from "@/components/ui/spinner"
import { forgotPasswordApi } from "@/services/auth"

export default function ForgotPasswordPage() {
  const [email, setEmail] = React.useState("")
  const [isLoading, setIsLoading] = React.useState(false)
  const [error, setError] = React.useState<string | undefined>()
  const [sent, setSent] = React.useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError(undefined)
    try {
      await forgotPasswordApi(email)
      setSent(true)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4" style={{ backgroundColor: "#0F0F0F" }}>
      <Card className="w-full max-w-md border" style={{ backgroundColor: "#1A1A1A", borderColor: "#2A2A2A" }}>
        <CardHeader className="text-center">
          <div className="mb-2 flex justify-center">
            <span className="text-2xl font-bold" style={{ color: "#E1306C" }}>Calendo</span>
          </div>
          <CardTitle className="text-xl" style={{ color: "#F5F5F5" }}>Reset your password</CardTitle>
          <CardDescription style={{ color: "#888888" }}>
            Enter your email and we&apos;ll send you a reset link
          </CardDescription>
        </CardHeader>

        {sent ? (
          <CardContent>
            <div
              className="rounded-md px-4 py-3 text-sm text-center"
              style={{ backgroundColor: "rgba(225,48,108,0.08)", border: "1px solid rgba(225,48,108,0.25)", color: "#F5F5F5" }}
            >
              Check your email for a reset link
            </div>
          </CardContent>
        ) : (
          <form onSubmit={handleSubmit}>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="email" style={{ color: "#F5F5F5" }}>Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={isLoading}
                  className="placeholder:text-[#888888]"
                  style={{ backgroundColor: "#0F0F0F", borderColor: "#2A2A2A", color: "#F5F5F5" }}
                />
              </div>
              {error && (
                <div
                  className="rounded-md px-3 py-2 text-sm"
                  style={{ backgroundColor: "rgba(225,48,108,0.1)", color: "#E1306C", border: "1px solid rgba(225,48,108,0.3)" }}
                >
                  {error}
                </div>
              )}
            </CardContent>
            <CardFooter className="flex flex-col gap-4">
              <Button
                type="submit"
                className="w-full text-white"
                disabled={isLoading}
                style={{ backgroundColor: "#E1306C" }}
              >
                {isLoading ? <><Spinner className="mr-2" /> Sending...</> : "Send reset link"}
              </Button>
            </CardFooter>
          </form>
        )}

        <CardFooter className="justify-center">
          <p className="text-sm" style={{ color: "#888888" }}>
            Remember your password?{" "}
            <Link href="/login" className="font-medium hover:underline underline-offset-4" style={{ color: "#E1306C" }}>
              Sign in
            </Link>
          </p>
        </CardFooter>
      </Card>
    </div>
  )
}
