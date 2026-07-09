import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server proxies /api -> the Campus FastAPI (campus.api.server) on :8000.
// In production, serve the built dist/ behind the same API origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
      "/demo": { target: "http://localhost:8000", changeOrigin: true },
      "/demo_a": { target: "http://localhost:8000", changeOrigin: true },
      "/demo_b": { target: "http://localhost:8000", changeOrigin: true },
      "/demo_c": { target: "http://localhost:8000", changeOrigin: true },
      "/agent": { target: "http://localhost:8000", changeOrigin: true },
      "/settings": { target: "http://localhost:8000", changeOrigin: true },
      "/learning": { target: "http://localhost:8000", changeOrigin: true },
      "/research": { target: "http://localhost:8000", changeOrigin: true },
      "/notes": { target: "http://localhost:8000", changeOrigin: true },
      "/life": { target: "http://localhost:8000", changeOrigin: true },
      "/club": { target: "http://localhost:8000", changeOrigin: true },
      "/career": { target: "http://localhost:8000", changeOrigin: true },
      "/memory": { target: "http://localhost:8000", changeOrigin: true },
      "/onboarding": { target: "http://localhost:8000", changeOrigin: true },
      "/profile": { target: "http://localhost:8000", changeOrigin: true },
      "/tasks": { target: "http://localhost:8000", changeOrigin: true },
      "/push": { target: "http://localhost:8000", changeOrigin: true },
      "/runs": { target: "http://localhost:8000", changeOrigin: true },
      "/calendar": { target: "http://localhost:8000", changeOrigin: true },
      "/anniversaries": { target: "http://localhost:8000", changeOrigin: true },
      "/daily_log": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
  build: { outDir: "dist", sourcemap: true },
});
