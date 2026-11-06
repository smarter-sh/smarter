/**
 * Vite configuration of @smarter/console, the single-page web console (ADR-035).
 *
 * - `npm run dev` serves the console at http://localhost:5173/. Every path that belongs to the backend is
 *   proxied to the Django dev server at http://localhost:9357, so the browser sees one origin, and Django's
 *   session and CSRF cookies work as they do in production.
 * - `npm run build` writes index.html and its assets into Django's static folder,
 *   smarter/static/react/@smarter/console/, from which Django serves the console's pages until the console
 *   moves to its own host.
 * - console.debug() calls are removed from production builds.
 */
import { defineConfig, type ConfigEnv, type ProxyOptions } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import packageJson from "./package.json" with { type: "json" };

const packageName = packageJson.name;

/** The Django dev server, which serves the backend while the console runs on Vite's dev server. */
const DJANGO = "http://localhost:9357";

/**
 * The paths that belong to the backend: its apis, Django admin, social sign-in, the translation
 * catalogs, static files, and the Terminal's WebSocket. Everything else is the console's.
 */
const BACKEND_PATHS = ["/api", "/admin", "/social-auth", "/i18n", "/jsi18n", "/static"];

function backendProxy(): Record<string, ProxyOptions> {
  const proxy: Record<string, ProxyOptions> = {};
  for (const backendPath of BACKEND_PATHS) {
    proxy[backendPath] = { target: DJANGO };
  }
  proxy["/ws"] = { target: DJANGO, ws: true };
  return proxy;
}

export default defineConfig(({ command }: ConfigEnv) => ({
  plugins: [react()],
  base: command === "serve" ? "/" : `/static/react/${packageName}/`,
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },
  build: {
    manifest: "manifest.json",
    outDir: `../../../smarter/static/react/${packageName}`,
    emptyOutDir: true,
    rolldownOptions: {
      output: {
        entryFileNames: "assets/[name]-[hash].js",
        chunkFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
        // The Oxc minifier's way of removing console.debug() calls, which can log sensitive data.
        minify: {
          compress: {
            treeshake: {
              manualPureFunctions: ["console.debug"],
            },
          },
        },
      },
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    proxy: backendProxy(),
  },
}));
