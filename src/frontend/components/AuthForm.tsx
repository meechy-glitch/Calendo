"use client"
import * as React from "react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Spinner } from "@/components/ui/spinner"

export type AuthMode = "login" | "register"

export interface AuthFormProps {
  mode: AuthMode
  onSubmit: (email: string, password: string) => void
  onToggleMode: () => void
  isLoading?: boolean
  error?: string
}

export function AuthForm({ mode, onSubmit, onToggleMode, isLoading = false, error }: AuthFormProps) {
  const [email, setEmail] = React.useState("")
  const [password, setPassword] = React.useState("")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit(email, password)
  }

  const isLogin = mode === "login"

  return (
    <div className="flex min-h-screen items-center justify-center p-4" style={{ backgroundColor: "#0F0F0F" }}>
      <Card
        className="w-full max-w-md border"
        style={{ backgroundColor: "#1A1A1A", borderColor: "#2A2A2A" }}
      >
        <CardHeader className="text-center">
          <div className="mb-2 flex justify-center">
            <span className="text-2xl font-bold" style={{ color: "#E1306C" }}>Calendo</span>
          </div>
          <CardTitle className="text-xl" style={{ color: "#F5F5F5" }}>
            {isLogin ? "Welcome back" : "Create an account"}
          </CardTitle>
          <CardDescription style={{ color: "#888888" }}>
            {isLogin ? "Sign in to manage your content schedule" : "Get started with Calendo today"}
          </CardDescription>
        </CardHeader>

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

            <div className="space-y-2">
              <Label htmlFor="password" style={{ color: "#F5F5F5" }}>Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                disabled={isLoading}
                className="placeholder:text-[#888888]"
                style={{ backgroundColor: "#0F0F0F", borderColor: "#2A2A2A", color: "#F5F5F5" }}
              />
              {!isLogin && (
                <p className="text-xs" style={{ color: "#888888" }}>Must be at least 8 characters</p>
              )}
              {isLogin && (
                <div className="text-right">
                  <Link
                    href="/forgot-password"
                    className="text-xs hover:underline underline-offset-4"
                    style={{ color: "#888888" }}
                  >
                    Forgot password?
                  </Link>
                </div>
              )}
            </div>

            {error && (
              <div
                className="rounded-md px-3 py-2 text-sm"
                style={{
                  backgroundColor: "rgba(225, 48, 108, 0.1)",
                  color: "#E1306C",
                  border: "1px solid rgba(225, 48, 108, 0.3)",
                }}
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
              {isLoading ? (
                <>
                  <Spinner className="mr-2" />
                  {isLogin ? "Signing in..." : "Creating account..."}
                </>
              ) : (
                <>{isLogin ? "Sign in" : "Create account"}</>
              )}
            </Button>

            <p className="text-center text-sm" style={{ color: "#888888" }}>
              {isLogin ? "Don't have an account?" : "Already have an account?"}{" "}
              <button
                type="button"
                onClick={onToggleMode}
                disabled={isLoading}
                className="font-medium underline-offset-4 hover:underline disabled:pointer-events-none disabled:opacity-50"
                style={{ color: "#E1306C" }}
              >
                {isLogin ? "Sign up" : "Sign in"}
              </button>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  )
}
