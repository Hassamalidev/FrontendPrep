import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    // import.meta.dirname rather than __dirname: the native config loader
    // does not provide CJS globals, and URL().pathname yields "/C:/..." on
    // Windows, which rolldown rejects.
    alias: { "@": path.resolve(import.meta.dirname, "./src") },
  },
  server: {
    port: 5173,
    // The API is same-origin in development, so the browser never sees CORS and
    // the token handling behaves exactly as it will behind a single domain.
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    // Sourcemaps are worth the build time: this deploys to Vercel's free tier
    // where there is no other way to read a production stack trace.
    sourcemap: true,
  },
});
