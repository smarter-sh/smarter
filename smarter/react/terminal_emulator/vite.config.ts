import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig(({ command }) => ({
  plugins: [react()],
  // runtime builds are saved into the Django static directory so that these
  // files can be included in the Django collectstatic process and served by
  // Django at runtime. On the other hand, in development we want to rely on
  // Vite's dev server to serve these files, so we set the base to '/'.
  base: command === "serve" ? "/" : "/static/react/terminal_emulator/",
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    outDir: "../../smarter/static/react/terminal_emulator",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        entryFileNames: "assets/index.js",
        chunkFileNames: "assets/[name].js",
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
      "/dashboard/logs/api": "http://localhost:9357",
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
      "/static/react/terminal_emulator/": {
        target: "http://localhost:5173",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/static\/terminal_emulator\//, "/"),
      },
    },
  },
}));
