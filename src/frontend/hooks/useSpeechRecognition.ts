"use client"
import * as React from "react"

export interface SpeechRecognitionHook {
  transcript: string
  isListening: boolean
  supported: boolean
  start: () => void
  stop: () => void
}

export function useSpeechRecognition(): SpeechRecognitionHook {
  const [transcript, setTranscript] = React.useState("")
  const [isListening, setIsListening] = React.useState(false)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recRef = React.useRef<any>(null)

  const supported =
    typeof window !== "undefined" &&
    ("SpeechRecognition" in window || "webkitSpeechRecognition" in window)

  const start = React.useCallback(() => {
    if (!supported) return
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const win = window as any
    const SR = win.SpeechRecognition ?? win.webkitSpeechRecognition
    const rec = new SR()
    rec.lang = "en-US"
    rec.interimResults = false
    rec.maxAlternatives = 1
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    rec.onresult = (e: any) => setTranscript(e.results[0][0].transcript)
    rec.onend = () => setIsListening(false)
    rec.onerror = () => setIsListening(false)
    recRef.current = rec
    rec.start()
    setIsListening(true)
  }, [supported])

  const stop = React.useCallback(() => {
    recRef.current?.stop()
    setIsListening(false)
  }, [])

  return { transcript, isListening, supported, start, stop }
}
