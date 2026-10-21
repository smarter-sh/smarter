/**
 * Vite configuration for @smarter.sh/ui-widgets.
 *
 * - `npm run build:lib` (`vite build --mode lib`): builds the library into dist/, as
 *   ui-widgets.es.js and ui-widgets.css. Then tsc -p tsconfig.lib.json writes its type
 *   declarations into dist/types/.
 * - Storybook and Vitest load the default configuration, which only adds React and the @/ alias.
 *
 * The library imports its own stylesheet (the output banner), so a page's bundler loads the widgets'
 * styles along with the widgets. Pages without a bundler link "@smarter.sh/ui-widgets/style.css".
 *
 * React is a peer dependency, left to the page's bundler. @smarter/common, which is not published
 * to npm, is bundled: the widgets call only its gettext() and interpolateNodes(), which read the
 * page's Django JavaScript catalog when there is one, and fall back to English when there isn't.
 * @smarter/didyouknow, also not on npm, is bundled too: the DidYouKnow widget's facts.
 *
 * Library mode inlines the images that the widgets import, so the package has no asset files.
 * The Keen theme's own images, such as the Sdk widget's illustration, stay at their /static/assets/
 * paths, which the page serves along with the Keen stylesheet.
 */
import { defineConfig, type ConfigEnv, type UserConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

const resolve = {
  alias: {
    "@": path.resolve(import.meta.dirname, "./src"),
  },
};

/** The npm library: @smarter.sh/ui-widgets. */
function libraryConfig(): UserConfig {
  // vite build keeps a NODE_ENV that the shell sets. With NODE_ENV=development, the library would
  // bundle React's development JSX runtime, which require()s react and fails as an ES module.
  process.env.NODE_ENV = "production";
  return {
    plugins: [react()],
    resolve,
    build: {
      outDir: "dist",
      emptyOutDir: true,
      sourcemap: true,
      lib: {
        entry: path.resolve(import.meta.dirname, "src/index.tsx"),
        formats: ["es"],
        fileName: () => "ui-widgets.es.js",
        // the banner below imports it. Pages without a bundler link "@smarter.sh/ui-widgets/style.css".
        cssFileName: "ui-widgets",
      },
      rolldownOptions: {
        external: ["react", "react-dom", "react/jsx-runtime"],
        output: {
          banner: 'import "./ui-widgets.css";',
        },
      },
    },
  };
}

/** Storybook and Vitest. */
function defaultConfig(): UserConfig {
  return {
    plugins: [react()],
    resolve,
  };
}

export default defineConfig(({ mode }: ConfigEnv) => (mode === "lib" ? libraryConfig() : defaultConfig()));
