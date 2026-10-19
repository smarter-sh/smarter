/**
 * Vite configuration of the LLMClient architecture package, for its development page only (`npm run dev`), which
 * draws the example tree of src/mocks/fixtures.ts. The package has no build of its own: the Prompt Engineer's
 * Workbench (@smarter/workbench) imports its component, and its build bundles it.
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
  // the web console's global stylesheets, which index.html links, are served by the Django dev server.
  server: {
    proxy: {
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
    },
  },
});
