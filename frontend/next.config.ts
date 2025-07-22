import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export', // Changed to 'export' for static generation
  images: {
    unoptimized: true, // Required for static export
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**.amazonaws.com',
      },
      {
        protocol: 'https',
        hostname: '**.cloudfront.net',
      },
    ],
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api',
  },
  poweredByHeader: false,
  compress: true,
  reactStrictMode: true,
  trailingSlash: true, // Better for static hosting
};

export default nextConfig;
