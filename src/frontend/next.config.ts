import type { NextConfig } from "next"

const nextConfig: NextConfig = {
  allowedDevOrigins: ['*'],
  devIndicators: false,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: process.env.NODE_ENV === "production" 
          ? "https://calendo-api.onrender.com/:path*"
          : "http://localhost:8000/:path*",
      },
    ]
  },
}

export default nextConfig