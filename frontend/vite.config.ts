import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      // Forward /api/* to the backend in dev. In the Docker/Nginx stack this
      // is the host gateway (Nginx proxies /api -> api:5000). The client keeps
      // using relative /api paths, so production and dev behave the same.
      "/api": {
        target: process.env.VITE_BACKEND_URL || "http://127.0.0.1:5000",
        changeOrigin: true,
      },
    },
  },
});
