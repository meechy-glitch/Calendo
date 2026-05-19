"use client"
import { useEffect } from "react"

interface ToastProps {
  message: string
  type: "success" | "error"
  onClose: () => void
}

export function Toast({ message, type, onClose }: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(onClose, 3000)
    return () => clearTimeout(timer)
  }, [onClose])

  return (
    <div
      className="fixed bottom-6 left-6 z-50 flex max-w-sm items-center gap-3 rounded-lg px-4 py-3 shadow-lg"
      style={{
        backgroundColor: "#1A1A1A",
        borderTop: "1px solid #2A2A2A",
        borderRight: "1px solid #2A2A2A",
        borderBottom: "1px solid #2A2A2A",
        borderLeft: "4px solid #E1306C",
        color: type === "error" ? "#E1306C" : "#F5F5F5",
      }}
    >
      <span className="text-sm">{message}</span>
      <button
        onClick={onClose}
        className="ml-auto text-lg leading-none"
        style={{ color: "#888888" }}
        aria-label="Close"
      >
        ×
      </button>
    </div>
  )
}
