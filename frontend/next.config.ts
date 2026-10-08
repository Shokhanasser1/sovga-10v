import type { NextConfig } from "next";

// Адрес Django. Браузер ходит на /api/… этого же сайта, а Next.js проксирует запросы сюда.
const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  experimental: { globalNotFound: true },
  async rewrites() {
    // Next.js убирает завершающий слэш, а Django его требует — добавляем обратно.
    return [{ source: "/api/:path*", destination: `${API_URL}/api/:path*/` }];
  },
};

export default nextConfig;
