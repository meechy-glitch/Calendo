"use client"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { AuthForm } from "@/components/AuthForm"
import { loginApi } from "@/services/auth"

export default function LoginPage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | undefined>()

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
    <AuthForm
      mode="login"
      onSubmit={handleSubmit}
      onToggleMode={() => router.push("/register")}
      isLoading={isLoading}
      error={error}
    />
  )
}
