/**
 * Storybook configuration for Smarter Chat: `make serve`, or `npm run storybook`.
 *
 * This is self-contained, so that Storybook runs both in a plain clone of this repository and inside
 * the npm workspace of https://github.com/smarter-sh/smarter, where it is configured the same way as
 * the workspace's other packages (see storybook/main.ts there):
 *
 * - Stories are src/**\/*.stories.tsx, and docs are src/**\/*.mdx.
 * - @storybook/addon-docs generates a docs page for each component, from its stories and types.
 * - @storybook/addon-a11y checks each story for accessibility violations.
 * - MSW's service worker is served from .storybook/public, for the stories' mocked API requests,
 *   so the Smarter backend is not needed.
 * - Bootstrap and Bootstrap Icons are served from node_modules, at /fallback/, for when the Smarter
 *   web console's stylesheets are unavailable. See preview-head.html.
 *
 * Storybook's Vite builder loads vite.config.ts. Its build-only plugin, which writes manifest.json
 * into Django's static directory, is removed.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { StorybookConfig } from "@storybook/react-vite";
import type { PluginOption } from "vite";

const HERE = import.meta.dirname;
const PACKAGE_DIR = path.resolve(HERE, "..");

/** The vite.config.ts plugins that must not run in Storybook. */
const BUILD_ONLY_PLUGINS = new Set(["add-custom-manifest-data"]);

function withoutBuildOnlyPlugins(plugins: PluginOption[] | undefined): PluginOption[] {
  return (plugins ?? []).flat().filter((plugin) => {
    const name = plugin && typeof plugin === "object" && "name" in plugin ? plugin.name : undefined;
    return !name || !BUILD_ONLY_PLUGINS.has(name);
  });
}

/** The directory of an installed npm package's file, wherever npm installed it. */
function installedDir(specifier: string): string {
  return path.dirname(fileURLToPath(import.meta.resolve(specifier)));
}

const config: StorybookConfig = {
  stories: [path.join(PACKAGE_DIR, "src/**/*.mdx"), path.join(PACKAGE_DIR, "src/**/*.stories.@(ts|tsx)")],
  addons: ["@storybook/addon-docs", "@storybook/addon-a11y"],
  framework: "@storybook/react-vite",
  staticDirs: [
    path.join(HERE, "public"),
    { from: installedDir("bootstrap/dist/css/bootstrap.min.css"), to: "/fallback/bootstrap" },
    { from: installedDir("bootstrap-icons/font/bootstrap-icons.min.css"), to: "/fallback/bootstrap-icons" },
  ],
  previewHead: (head) => `${head}\n${fs.readFileSync(path.join(HERE, "preview-head.html"), "utf-8")}`,
  viteFinal: async (viteConfig) => ({
    ...viteConfig,
    plugins: withoutBuildOnlyPlugins(viteConfig.plugins),
    resolve: {
      ...viteConfig.resolve,
      alias: {
        ...(viteConfig.resolve?.alias as Record<string, string> | undefined),
        "@": path.join(PACKAGE_DIR, "src"),
      },
    },
  }),
};

export default config;
