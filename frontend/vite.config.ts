import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// The FastAPI backend (see backend/) serves the API on :8000. During development
// the Vite dev server proxies /v1 and /ws so the browser only ever talks to one origin.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/v1": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/ws": {
        target: "ws://127.0.0.1:8000",
        ws: true,
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        // Split the heaviest vendor libraries so the core shell parses fast.
        manualChunks: {
          markdown: ["react-markdown", "remark-gfm", "react-syntax-highlighter"],
        },
      },
    },
  },
});
