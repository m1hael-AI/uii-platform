import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_TELEGRAM_BOT_USERNAME: process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME,
  },
  allowedDevOrigins: [
    "https://36724636-864c-4f40-b98e-f1747f886c32-00-1cr9r37kvwh4.janeway.replit.dev",
    "http://36724636-864c-4f40-b98e-f1747f886c32-00-1cr9r37kvwh4.janeway.replit.dev",
    "*.replit.dev",
    "*.replit.app",
  ],
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "Cache-Control", value: "no-store, no-cache, must-revalidate" },
        ],
      },
    ];
  },
};

export default nextConfig;
