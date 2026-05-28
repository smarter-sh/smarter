import { defineConfig, type ConfigEnv, type PluginOption } from "vite";
import { execSync } from "child_process";
import react from "@vitejs/plugin-react";
import path from "path";
import packageJson from "./package.json" with { type: "json" };

const packageName = "terminal_emulator";

// We optionally push the build files to an S3 bucket in order to simplify Docker builds.
// This enables us to avoid having to use React build tools inside of Docker.
//
// Separately, we also create a CloudFront invalidation after each build so that
// we maintain the option of serving these files from Cloudfront in production (if
// we ever find a compelling reason to do so in the future).
const postBuildPlugin: PluginOption = {
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

export default defineConfig(({ command }: ConfigEnv) => ({
  plugins: [
    react(),
    postBuildPlugin,
  ],
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
  // Most of these cases stem from <link> elements added to this index.html
  // containing platform-wide stylesheets and scripts that originate from
  // and are served by the Django dev server. These are added to index.html
  // in order to keep this React dev environment as close to the runtime
  // environment as possible.
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
    },
  },
}));
