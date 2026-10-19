/**
 * Vite configuration of the server log viewer package, for its development page only (`npm run dev`), which
 * displays the example records of src/mocks/fixtures.ts. The package has no build of its own: the Prompt
 * Engineer's Workbench (@smarter/workbench) and the Prompt Passthrough (@smarter/prompt-passthrough) import its
 * component, and their builds bundle it.
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
