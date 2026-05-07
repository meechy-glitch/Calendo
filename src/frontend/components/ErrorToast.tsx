import { useEffect } from "react"

interface ErrorToastProps {
  message: string
  onClose: () => void
}

export function ErrorToast({ message, onClose }: ErrorToastProps) {
  useEffect(() => {
    const timer = setTimeout(onClose, 5000)
    return () => clearTimeout(timer)
  }, [onClose])

  return (
    <div
      className="fixed bottom-6 left-6 z-50 flex max-w-sm items-center gap-3 rounded-lg px-4 py-3 shadow-lg"
      style={{
        backgroundColor: "#1A1A1A",
        border: "1px solid #E1306C",
        color: "#F5F5F5",
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
