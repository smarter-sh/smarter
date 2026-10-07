/**
 * Vite Configuration for the Manifest Editor React App
 *
 * This configuration is the same as @smarter/prompt-passthrough's, without its
 * xterm.js chunking. It:
 *
 * - Builds the React assets into the Django static directory, for collectstatic.
 * - Injects build metadata (version, build time, environment) into the manifest for Django use.
 * - Proxies API and static asset requests to the Django development server during local development.
 * - Removes console.debug statements from production builds via the Oxc minifier
 *   to avoid leaking sensitive info.
 *
 * Integration:
 * - The manifest.json is used by Django templatetags to resolve hashed asset filenames for cache busting.
 *   See smarter.apps.dashboard.templatetags.react_manifest_editor.
 */
import { defineConfig, type ConfigEnv, type PluginOption } from "vite";
import react from "@vitejs/plugin-react";
import fs from "fs";
import path from "path";
import packageJson from "./package.json" with { type: "json" };

const packageName = packageJson.name;

/**
 * Vite Plugin: addCustomManifestData
 *
 * Injects custom metadata into the generated manifest.json file after each build:
 * buildTime, version and buildEnv. Django uses it to display build details.
 */
const addCustomManifestData: PluginOption = {
  name: "add-custom-manifest-data",
  writeBundle() {
    const manifestPath = path.resolve(
      import.meta.dirname,
      `../../../smarter/static/react/${packageName}/manifest.json`,
    );
    if (fs.existsSync(manifestPath)) {
      const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
      manifest._custom = {
        buildTime: new Date().toISOString(),
        version: packageJson.version,
        buildEnv: process.env.NODE_ENV || "development",
      };
      fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
    }
  },
};

export default defineConfig(({ command }: ConfigEnv) => ({
  plugins: [react(), addCustomManifestData],
  // Vite's dev server serves from '/'. Builds are served by Django from the static directory.
  base: command === "serve" ? "/" : `/static/react/${packageName}/`,
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },
  build: {
    // The manifest is used by Django templatetags to include the hashed file names.
    manifest: "manifest.json",
    // The build output is placed in the Django static directory, for collectstatic.
    outDir: `../../../smarter/static/react/${packageName}`,
    emptyOutDir: true,
    rolldownOptions: {
      output: {
        entryFileNames: "assets/[name]-[hash].js",
        chunkFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
        // Mark console.debug() calls as side-effect-free, so that the Oxc minifier
        // strips them from production builds (avoids leaking sensitive info).
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
  // In development, the platform-wide stylesheets and scripts in index.html, and the
  // api, are served by the Django dev server.
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
      [`/static/react/${packageName}/`]: {
        target: "http://localhost:5173",
        changeOrigin: true,
        rewrite: (path: string) => path.replace(new RegExp(`^/static/react/${packageName}/`), "/"),
      },
      "/static": {
        target: "http://localhost:9357",
        changeOrigin: true,
      },
    },
  },
}));
