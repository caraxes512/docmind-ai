/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Standalone output produces a self-contained server bundle (node_modules
  // pruned to only what's actually used) — this is what backend/../frontend
  // Dockerfile's runtime stage copies, instead of shipping the full
  // node_modules tree into the final image.
  output: "standalone",
  // Proxies /api/* to the FastAPI backend in local dev so the browser only
  // ever talks to same-origin URLs (avoids CORS complexity beyond what's
  // already configured backend-side in Step 5, and keeps the door open for
  // moving to same-origin cookie-based auth later — see lib/auth-context.tsx).
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}/api/:path*`,
      },
    ];
  },
  eslint: {
    // Warning: This allows production builds to successfully complete even if
    // your project has ESLint errors.
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
