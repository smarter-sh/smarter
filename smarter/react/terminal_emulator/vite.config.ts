import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";


export default defineConfig({
  plugins: [react()],
  base: process.env.NODE_ENV === 'development' ? '/' : '/static/terminal_emulator/',
  build: {
    outDir: "../../smarter/static/prompt_passthrough",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        entryFileNames: "assets/index.js",
        assetFileNames: "assets/[name][extname]",
      },
    },
  },
  server: {
    proxy: {
      '/api': 'http://localhost:9357',
      "/assets": {
        target: "http://localhost:9357", // Django dev server
        changeOrigin: true,
        rewrite: (path) => `/static${path}`,
      },
      "/common-styles.css": {
        target: "http://localhost:9357",
        changeOrigin: true,
        rewrite: (path) => `/static${path}`,
      },
      "/static/prompt_passthrough/": {
        target: "http://localhost:5173",
        changeOrigin: true,
          rewrite: (path) =>
          path.replace(/^\/static\/prompt_passthrough\//, "/"),
      },
    },
  },
});
