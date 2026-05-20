"use client"
import * as React from "react"
import { useRouter, useSearchParams } from "next/navigation"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Spinner } from "@/components/ui/spinner"
import { resetPasswordApi } from "@/services/auth"

function ResetPasswordForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const token = searchParams.get("token") ?? ""
  const [newPassword, setNewPassword] = React.useState("")
  const [confirmPassword, setConfirmPassword] = React.useState("")
  const [isLoading, setIsLoading] = React.useState(false)
  const [error, setError] = React.useState<string | undefined>()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match")
      return
    }
    if (newPassword.length < 8) {
      setError("Password must be at least 8 characters")
      return
    }
    setIsLoading(true)
    setError(undefined)
    try {
      await resetPasswordApi(token, newPassword)
      router.push("/login")
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong")
    } finally {
      setIsLoading(false)
    }
  }

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4" style={{ backgroundColor: "#0F0F0F" }}>
        <Card className="w-full max-w-md border" style={{ backgroundColor: "#1A1A1A", borderColor: "#2A2A2A" }}>
          <CardContent className="pt-6 text-center">
            <p style={{ color: "#888888" }}>Invalid reset link.</p>
            <Link href="/forgot-password" className="text-sm hover:underline underline-offset-4 mt-2 block" style={{ color: "#E1306C" }}>
              Request a new one
            </Link>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4" style={{ backgroundColor: "#0F0F0F" }}>
      <Card className="w-full max-w-md border" style={{ backgroundColor: "#1A1A1A", borderColor: "#2A2A2A" }}>
        <CardHeader className="text-center">
          <div className="mb-2 flex justify-center">
            <span className="text-2xl font-bold" style={{ color: "#E1306C" }}>Calendo</span>
          </div>
          <CardTitle className="text-xl" style={{ color: "#F5F5F5" }}>Choose a new password</CardTitle>
          <CardDescription style={{ color: "#888888" }}>Must be at least 8 characters</CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="new-password" style={{ color: "#F5F5F5" }}>New password</Label>
              <Input
                id="new-password"
                type="password"
                placeholder="••••••••"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={8}
                disabled={isLoading}
                className="placeholder:text-[#888888]"
                style={{ backgroundColor: "#0F0F0F", borderColor: "#2A2A2A", color: "#F5F5F5" }}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirm-password" style={{ color: "#F5F5F5" }}>Confirm password</Label>
              <Input
                id="confirm-password"
                type="password"
                placeholder="••••••••"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                minLength={8}
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
              {isLoading ? <><Spinner className="mr-2" /> Updating...</> : "Update password"}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  )
}

export default function ResetPasswordPage() {
  return (
    <React.Suspense fallback={null}>
      <ResetPasswordForm />
    </React.Suspense>
  )
}
