"use client"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { AuthForm } from "@/components/AuthForm"
import { registerApi, loginApi } from "@/services/auth"

export default function RegisterPage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | undefined>()

  const handleSubmit = async (email: string, password: string) => {
    setIsLoading(true)
    setError(undefined)
    try {
      await registerApi(email, password)
      const data = await loginApi(email, password)
      localStorage.setItem("token", data.access_token)
      localStorage.setItem("email", email)
      router.push("/dashboard")
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <AuthForm
      mode="register"
      onSubmit={handleSubmit}
      onToggleMode={() => router.push("/login")}
      isLoading={isLoading}
      error={error}
    />
  )
}
