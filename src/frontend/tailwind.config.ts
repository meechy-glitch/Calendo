import type { Config } from "tailwindcss"

const config: Config = {
  darkMode: ["class"],
  content: [
    "./*.{ts,tsx,html}",
    "./pages/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./api/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        "calendo-bg": "#0F0F0F",
        "calendo-surface": "#1A1A1A",
        "calendo-accent": "#E1306C",
        "calendo-text": "#F5F5F5",
        "calendo-muted": "#888888",
        "calendo-border": "#2A2A2A",
      },
    },
  },
  plugins: [],
}

export default config
