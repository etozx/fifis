import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server proxies /api to the backend so cookies are same-origin locally,
// sidestepping cross-site cookie friction during development.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_DEV_API_TARGET || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    // Split heavy third-party code into separate chunks so no single bundle
    // trips the 500 kB warning. Recharts (+ its d3 deps) is by far the largest,
    // so it gets its own chunk that only loads with the charts.
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) return undefined;
          if (
            id.includes("recharts") ||
            id.includes("/d3-") ||
            id.includes("victory-vendor")
          ) {
            return "charts";
          }
          if (id.includes("react-router") || id.includes("/react-dom/")) {
            return "react-vendor";
          }
          return undefined;
        },
      },
    },
  },
});
