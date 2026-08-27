"use client"
import * as React from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { AuthForm } from "@/components/AuthForm"
import { Toast } from "@/components/Toast"
import { loginApi } from "@/services/auth"

function LoginView() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [isLoading, setIsLoading] = React.useState(false)
  const [error, setError] = React.useState<string | undefined>()
  // Set by the account-deletion flow, which lands here after wiping the session.
  const [notice, setNotice] = React.useState(() =>
    searchParams.get("deleted") === "1" ? "Your account has been deleted" : undefined
  )

  const handleSubmit = async (email: string, password: string) => {
    setIsLoading(true)
    setError(undefined)
    try {
      const data = await loginApi(email, password)
      localStorage.setItem("token", data.access_token)
      localStorage.setItem("email", email)
      router.push("/dashboard")
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <>
      <AuthForm
        mode="login"
        onSubmit={handleSubmit}
        onToggleMode={() => router.push("/register")}
        isLoading={isLoading}
        error={error}
      />
      {notice && (
        <Toast message={notice} type="success" onClose={() => setNotice(undefined)} />
      )}
    </>
  )
}

export default function LoginPage() {
  return (
    <React.Suspense fallback={null}>
      <LoginView />
    </React.Suspense>
  )
}
