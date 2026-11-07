/**
 * Vite configuration of the LLM Host Compute list package, for its development page only (`npm run dev`). The package has
 * no build of its own: the single-page console (@smarter/console) imports its component, and its build bundles it.
 *
 * The development page calls the Django dev server's list api, and the web console's global stylesheets, which
 * index.html links, are served by the Django dev server too.
 */
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/api": "http://localhost:9357",
      "/assets": {
        target: "http://localhost:9357",
        changeOrigin: true,
        rewrite: (path: string) => `/static${path}`,
      },
      "/common-styles.css": {
        target: "http://localhost:9357",
        changeOrigin: true,
        rewrite: (path: string) => `/static${path}`,
      },
      "/static": {
        target: "http://localhost:9357",
        changeOrigin: true,
      },
    },
  },
});
