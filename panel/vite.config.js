import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "https://api:18443",
        changeOrigin: true,
        secure: false
      }
    }
  }
});
