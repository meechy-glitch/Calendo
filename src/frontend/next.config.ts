import type { NextConfig } from "next"

const nextConfig: NextConfig = {
  allowedDevOrigins: ['172.20.10.3', '192.168.100.209'],
  devIndicators: false,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/:path*",
      },
    ]
  },
}

export default nextConfig
