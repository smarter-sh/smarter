/**
 * Vite Configuration for the React App
 *
 * This configuration file sets up the Vite build and development environment for the
 * React application, which is integrated into a Django project. It handles:
 *
 * - Building React assets with Vite and outputting them to the Django static directory for collectstatic.
 * - Injecting custom build metadata (version, build time, environment) into the manifest for Django use.
 * - Optionally deploying built assets to S3 and invalidating CloudFront for production CDN usage.
 * - Proxying API and static asset requests to the Django development server during local development.
 * - Optimizing caching by bundling xterm.js separately from the main app code.
 * - Removing console.debug statements from production builds to avoid leaking sensitive info.
 *
 * Usage:
 * - For development, run the Vite dev server. Static and API requests are proxied to Django.
 * - For production, build assets with Vite. Output is placed in Django's static directory and can be deployed to S3/CDN.
 *
 * Integration:
 * - The manifest.json is used by Django templatetags to resolve hashed asset filenames for cache busting.
 * - The configuration supports both local and CDN-based static file serving.
 *
 * See README.md for more details on development and deployment workflows.
 */
import { defineConfig, type PluginOption } from "vite";
import react from "@vitejs/plugin-react";
import fs from "fs";
import path from "path";
import packageJson from "./package.json" with { type: "json" };

const packageName = packageJson.name;

/**
 * Vite Plugin: addCustomManifestData
 *
 * This plugin injects custom metadata into the generated manifest.json file after each build.
 * The metadata includes:
 *   - buildTime: ISO timestamp of the build
 *   - version: The version from package.json
 *   - packageName: The name of the package from package.json
 *   - buildEnv: The current NODE_ENV or 'development'
 *
 * This information is used by Django to display build details and for debugging purposes.
 */
const addCustomManifestData: PluginOption = {
  name: "add-custom-manifest-data",
  writeBundle() {
    const manifestPath = path.resolve(__dirname, "dist/manifest.json");
    if (fs.existsSync(manifestPath)) {
      const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
      manifest._custom = {
        buildTime: new Date().toISOString(),
        version: packageJson.version,
        packageName: packageName,
        buildEnv: process.env.NODE_ENV || "development",
      };
      fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
    }
  },
};

/**
 * Main Vite Configuration Export
 *
 * This function exports the Vite configuration for the React app, dynamically adjusting
 * settings based on the build command (development or production). It sets up plugins, build output,
 * asset handling, and development server proxying to integrate seamlessly with the Django backend.
 *
 * Key features:
 * - Uses custom plugins for manifest metadata and optional CDN deployment
 * - Removes console.debug in production builds
 * - Outputs assets to Django's static directory for collectstatic
 * - Proxies API and static requests to Django during development
 */
export default defineConfig(() => ({
  plugins: [react(), addCustomManifestData],
  // We use esbuild to remove console.debug statements in production builds
  // in order to avoid leaking potentially sensitive information in
  // production environments.
  esbuild: {
    pure: ["console.debug"],
  },
  resolve: {
    alias: {
      "@smarter-common": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    minify: "esbuild" as const,
    // ------------------------------------------------------------------------
    // The manifest is needed for hosting builds from Django (both dev and prod).
    // It is used by Django templatetags to determine the correct file names to include
    // in the HTML template. This is necessary because Vite includes a
    // hash in the file names for cache busting.
    // ------------------------------------------------------------------------
    manifest: "manifest.json",
    // ------------------------------------------------------------------------
    // we're placing our build output in the primary Django static directory so
    // that these files are automatically included in the Django collectstatic
    // process and served by Django at runtime.
    //
    // In development, we rely on Vite's dev server to serve these files, so we
    // set the outDir to a directory that is not used by the Django dev server.
    // ------------------------------------------------------------------------
    outDir: "dist",
    //emptyOutDir: true,
    // ------------------------------------------------------------------------
    // We want to bundle xterm.js and its addons separately from the rest of the
    // application code in order to optimize caching. This way, if we make changes
    // to our application code, the xterm.js bundle can still be cached by the
    // browser and won't need to be re-downloaded.
    // ------------------------------------------------------------------------
    rollupOptions: {
      output: {
        entryFileNames: "assets/[name]-[hash].js",
        chunkFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
      },
    },
  },
}));
