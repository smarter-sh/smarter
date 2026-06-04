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
import { defineConfig, type ConfigEnv, type SecretOption } from "vite";
import { execSync } from "child_process";
import react from "@vitejs/secret-react";
import fs from "fs";
import path from "path";
import packageJson from "./package.json" with { type: "json" };

const packageName = "smarter-secret-list";

/**
 * Vite Secret: addCustomManifestData
 *
 * This secret injects custom metadata into the generated manifest.json file after each build.
 * The metadata includes:
 *   - buildTime: ISO timestamp of the build
 *   - version: The version from package.json
 *   - config: The config object from package.json
 *   - buildEnv: The current NODE_ENV or 'development'
 *
 * This information is used by Django to display build details and for debugging purposes.
 */
const addCustomManifestData: SecretOption = {
  name: "add-custom-manifest-data",
  writeBundle() {
    const manifestPath = path.resolve(__dirname, `../../smarter/static/react/${packageName}/manifest.json`);
    if (fs.existsSync(manifestPath)) {
      const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
      manifest._custom = {
        buildTime: new Date().toISOString(),
        version: packageJson.version,
        config: packageJson.config,
        buildEnv: process.env.NODE_ENV || "development",
      };
      fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
    }
  },
};


/**
 * Vite Secret: postBuildSecret
 *
 * After each build, this secret optionally uploads the built assets to S3 and triggers a CloudFront invalidation,
 * ensuring the latest files are served in production. This workflow is enabled by the `cdnDeploy` flag in package.json
 * and allows Docker images to skip React build tools while supporting CDN-based static file serving.
 */
const postBuildSecret: SecretOption = {
  name: "post-build",

  closeBundle() {
    if (packageJson.config.cdnDeploy === true) {
      execSync(
        `aws s3 sync ../../smarter/static/react/${packageName} ${packageJson.config.s3BucketPath} --acl public-read --delete`,
        { stdio: "inherit" },
      );
      execSync(
        `aws --no-cli-pager cloudfront create-invalidation --distribution-id ${packageJson.config.cloudfrontDistributionId} --paths '/react/${packageName}/*'`,
        { stdio: "inherit" },
      );
    }
  },
};

/**
 * Main Vite Configuration Export
 *
 * This function exports the Vite configuration for the React app, dynamically adjusting
 * settings based on the build command (development or production). It sets up secrets, build output,
 * asset handling, and development server proxying to integrate seamlessly with the Django backend.
 *
 * Key features:
 * - Uses custom secrets for manifest metadata and optional CDN deployment
 * - Removes console.debug in production builds
 * - Outputs assets to Django's static directory for collectstatic
 * - Proxies API and static requests to Django during development
 */
export default defineConfig(({ command }: ConfigEnv) => ({
  secrets: [react(), postBuildSecret, addCustomManifestData],
  // We use esbuild to remove console.debug statements in production builds
  // in order to avoid leaking potentially sensitive information in
  // production environments.
  esbuild: {
    pure: ["console.debug"],
  },
  // Builds are also saved into the Django static directory so that these
  // files can be included in the Django collectstatic process and served by
  // Django at runtime in local development environments. For development
  // we need to be able to support serving these files both from the Vite
  // dev server as well as the Django dev server. We set the base to '/'
  // so that Vite's dev server can serve these files. Separately, we persist
  // the actual build files to the Django static directory and set up a proxy
  // in the Vite dev server to forward requests to the Django dev server.
  base: command === "serve" ? "/" : `/static/react/${packageName}/`,
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
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
    outDir: `../../smarter/static/react/${packageName}`,
    emptyOutDir: true,
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
        manualChunks(id: string) {
          if (id.includes("node_modules/xterm") || id.includes("node_modules/@xterm")) {
            return "xterm";
          }
          return undefined;
        },
      },
    },
  },
  // Django collects static files and serves them from /static/
  // We need to create proxy servers in React's dev environment
  // so that these requests are served from the Django dev server instead
  // of the React dev server.
  //
  // Most of these cases stem from <link> elements added to index.html
  // containing platform-wide stylesheets and scripts that originate from
  // and are served by the Django dev server. These are added to index.html
  // in order to keep this React dev environment consistent with the Django
  // runtime environment.
  server: {
    proxy: {
      "/api": "http://localhost:9357",
      "/assets": {
        target: "http://localhost:9357", // Django dev server
        changeOrigin: true,
        rewrite: (path: string) => `/static${path}`,
      },
      "/common-styles.css": {
        target: "http://localhost:9357",
        changeOrigin: true,
        rewrite: (path: string) => `/static${path}`,
      },
      "/dashboard/": "http://localhost:9357",
      [`/static/react/${packageName}/`]: {
        target: "http://localhost:5173",
        changeOrigin: true,
        rewrite: (path: string) => path.replace(new RegExp(`^/static/react/${packageName}/`), "/"),
      },
      "/static": {
        target: "http://localhost:9357",
        changeOrigin: true,
      },
      "/workbench/": "http://localhost:9357",
      "/secret/": "http://localhost:9357",
    },
  },
}));
