"use client"
import * as React from "react"
import { X, Send, Bot, Mic, Loader2, Trash2 } from "lucide-react"
import { sendChat, transcribeAudio, type ChatMessage, type ChatChange } from "@/services/ai"
import { useSpeechRecognition } from "@/hooks/useSpeechRecognition"

interface ChatPanelProps {
  onClose: () => void
  onChanges: (changes: ChatChange[]) => void
  embedded?: boolean
}

// Persist the conversation in sessionStorage so it survives switching between
// dashboard tabs (which unmounts this component) but is cleared when the browser
// tab/window is closed — i.e. it does not leak across browser sessions.
const STORAGE_KEY = "calendo.assistant.history"

function loadHistory(): ChatMessage[] {
  if (typeof window === "undefined") return []
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function ChatPanel({ onClose, onChanges, embedded }: ChatPanelProps) {
  const [messages, setMessages] = React.useState<ChatMessage[]>(loadHistory)
  const [input, setInput] = React.useState("")
  const [loading, setLoading] = React.useState(false)
  const bottomRef = React.useRef<HTMLDivElement>(null)
  const textareaRef = React.useRef<HTMLTextAreaElement>(null)

  const { transcript, isListening, supported, start, stop } = useSpeechRecognition()
  const [isRecordingFallback, setIsRecordingFallback] = React.useState(false)
  const [transcribing, setTranscribing] = React.useState(false)
  const mediaRecorderRef = React.useRef<MediaRecorder | null>(null)
  const chunksRef = React.useRef<Blob[]>([])

  const canFallback = typeof window !== "undefined" && typeof window.MediaRecorder !== "undefined"
  const showMicButton = supported || canFallback
  const isActivelyRecording = isListening || isRecordingFallback

  React.useEffect(() => {
    if (transcript) setInput(transcript)
  }, [transcript])

  const handleMicClick = async () => {
    if (supported) {
      isListening ? stop() : start()
      return
    }
    if (isRecordingFallback) {
      mediaRecorderRef.current?.stop()
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data) }
      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        setIsRecordingFallback(false)
        setTranscribing(true)
        try {
          const blob = new Blob(chunksRef.current, { type: "audio/webm" })
          const result = await transcribeAudio(blob)
          setInput(result.text)
        } catch { /* silently fail — user can type manually */ }
        finally { setTranscribing(false) }
      }
      mediaRecorderRef.current = recorder
      recorder.start()
      setIsRecordingFallback(true)
    } catch { /* mic permission denied */ }
  }

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, loading])

  // Persist conversation across tab switches within the same browser session.
  React.useEffect(() => {
    if (typeof window === "undefined") return
    try {
      if (messages.length > 0) {
        window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(messages))
      } else {
        window.sessionStorage.removeItem(STORAGE_KEY)
      }
    } catch { /* storage full or unavailable — keep the in-memory conversation */ }
  }, [messages])

  const handleClear = () => {
    setMessages([])
    setInput("")
    try { window.sessionStorage.removeItem(STORAGE_KEY) } catch { /* ignore */ }
    textareaRef.current?.focus()
  }

  const handleSend = async () => {
    const text = input.trim()
    if (!text || loading) return

    const userMsg: ChatMessage = { role: "user", content: text }
    const nextMessages = [...messages, userMsg]
    setMessages(nextMessages)
    setInput("")
    setLoading(true)

    try {
      const result = await sendChat(nextMessages)
      setMessages((prev) => [...prev, { role: "assistant", content: result.assistant_reply }])
      if (result.changes.length > 0) {
        onChanges(result.changes)
      }
    } catch (err: unknown) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: err instanceof Error ? `Error: ${err.message}` : "Something went wrong. Please try again.",
        },
      ])
    } finally {
      setLoading(false)
      textareaRef.current?.focus()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div
      className={embedded
        ? "flex h-full flex-col"
        : "fixed bottom-0 right-4 z-50 flex w-[360px] flex-col rounded-t-xl border shadow-2xl"
      }
      style={embedded
        ? { backgroundColor: "#1A1A1A" }
        : { backgroundColor: "#1A1A1A", borderColor: "#2A2A2A", height: "500px" }
      }
    >
      {/* Header */}
      <div
        className="flex flex-shrink-0 items-center justify-between border-b px-4 py-3"
        style={{ borderColor: "#2A2A2A" }}
      >
        <div className="flex items-center gap-2">
          <Bot size={16} style={{ color: "#E1306C" }} />
          <span className="text-sm font-medium" style={{ color: "#F5F5F5" }}>
            Calendo AI
          </span>
        </div>
        <div className="flex items-center gap-1">
          {messages.length > 0 && (
            <button
              onClick={handleClear}
              className="flex items-center gap-1 rounded px-1.5 py-1 text-[11px] transition-colors hover:bg-[#2A2A2A]"
              style={{ color: "#888888" }}
              aria-label="Clear conversation"
              title="Clear conversation"
            >
              <Trash2 size={13} />
              <span>Clear</span>
            </button>
          )}
          {!embedded && (
            <button
              onClick={onClose}
              className="rounded p-1 transition-colors hover:bg-[#2A2A2A]"
              style={{ color: "#888888" }}
              aria-label="Close"
            >
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 flex flex-col gap-3 min-h-0">
        {messages.length === 0 && (
          <div className="flex flex-col gap-2 mt-2">
            <p className="text-xs" style={{ color: "#888888" }}>
              Ask me to create, update, or reschedule posts. Try:
            </p>
            {[
              "What's on my calendar this week?",
              "Plan 3 Instagram posts for next week",
              "Move all my Tuesday posts to Wednesday",
            ].map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                onClick={() => setInput(suggestion)}
                className="w-full rounded-md border px-3 py-2 text-left text-xs transition-colors hover:border-[#E1306C]"
                style={{ backgroundColor: "#0F0F0F", borderColor: "#2A2A2A", color: "#888888" }}
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className="max-w-[85%] rounded-xl px-3 py-2 text-xs leading-relaxed"
              style={
                msg.role === "user"
                  ? { backgroundColor: "#E1306C", color: "#F5F5F5" }
                  : { backgroundColor: "#2A2A2A", color: "#F5F5F5", whiteSpace: "pre-wrap" }
              }
            >
              {msg.content}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div
              className="rounded-xl px-3 py-2 text-xs"
              style={{ backgroundColor: "#2A2A2A", color: "#888888" }}
            >
              Thinking…
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div
        className="border-t px-3 py-3 flex-shrink-0"
        style={{ borderColor: "#2A2A2A" }}
      >
        <div
          className="flex items-end gap-2 rounded-lg border px-3 py-2"
          style={{ backgroundColor: "#0F0F0F", borderColor: "#2A2A2A" }}
        >
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message Calendo AI…"
            rows={1}
            className="flex-1 resize-none bg-transparent text-xs outline-none placeholder:text-[#555555]"
            style={{ color: "#F5F5F5", maxHeight: "80px" }}
          />
          {showMicButton && (
            <button
              type="button"
              onClick={handleMicClick}
              disabled={transcribing}
              className={`flex-shrink-0 rounded p-1 transition-colors disabled:opacity-40${isActivelyRecording ? " animate-pulse" : ""}`}
              style={{ color: isActivelyRecording ? "#E1306C" : "#555555" }}
              aria-label={isActivelyRecording ? "Stop recording" : "Voice input"}
            >
              {transcribing ? <Loader2 size={14} className="animate-spin" /> : <Mic size={14} />}
            </button>
          )}
          <button
            type="button"
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="flex-shrink-0 rounded p-1 transition-colors disabled:opacity-40"
            style={{ color: input.trim() && !loading ? "#E1306C" : "#555555" }}
            aria-label="Send"
          >
            <Send size={14} />
          </button>
        </div>
        <p className="mt-1.5 text-center text-[10px]" style={{ color: "#555555" }}>
          Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}
