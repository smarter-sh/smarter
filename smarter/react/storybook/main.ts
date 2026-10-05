/**
 * Shared Storybook configuration for every package in this workspace.
 *
 * Each package's .storybook/main.ts calls smarterStorybookConfig(import.meta.dirname), so that
 * all of the packages' Storybooks are configured the same way:
 *
 * - Stories are the package's src/**\/*.stories.tsx files, and its src/**\/*.mdx docs.
 * - @storybook/addon-docs generates a docs page for each component, from its stories and types.
 * - @storybook/addon-a11y checks each story for accessibility violations.
 * - @smarter/common resolves to its TypeScript source, so that stories never depend on a stale build.
 * - MSW's service worker is served from storybook/public, for the stories' mocked API requests.
 * - The Smarter web console's stylesheets are loaded from the Django dev server, as in
 *   each package's index.html, so that components look as they do in the web console.
 *
 * Storybook's Vite builder loads the package's vite.config.ts. Its build plugins, which write
 * manifest.json into Django's static directory and can upload the build to S3, are removed.
 */
import fs from "node:fs";
import path from "node:path";
import type { StorybookConfig } from "@storybook/react-vite";
import type { PluginOption } from "vite";

const HERE = import.meta.dirname;
const WORKSPACE = path.resolve(HERE, "..");
const COMMON_SRC = path.join(WORKSPACE, "packages", "smarter-common", "src", "index.tsx");

/** The package build plugins that must not run in Storybook. See each package's vite.config.ts. */
const BUILD_ONLY_PLUGINS = new Set(["post-build", "add-custom-manifest-data"]);

function withoutBuildOnlyPlugins(plugins: PluginOption[] | undefined): PluginOption[] {
  return (plugins ?? []).flat().filter((plugin) => {
    const name = plugin && typeof plugin === "object" && "name" in plugin ? plugin.name : undefined;
    return !name || !BUILD_ONLY_PLUGINS.has(name);
  });
}

export function smarterStorybookConfig(storybookDir: string): StorybookConfig {
  const packageDir = path.resolve(storybookDir, "..");
  return {
    stories: [path.join(packageDir, "src/**/*.mdx"), path.join(packageDir, "src/**/*.stories.@(ts|tsx)")],
    addons: ["@storybook/addon-docs", "@storybook/addon-a11y"],
    framework: "@storybook/react-vite",
    staticDirs: [path.join(HERE, "public")],
    previewHead: (head) => `${head}\n${fs.readFileSync(path.join(HERE, "preview-head.html"), "utf-8")}`,
    viteFinal: async (config) => ({
      ...config,
      plugins: withoutBuildOnlyPlugins(config.plugins),
      resolve: {
        ...config.resolve,
        alias: {
          ...(config.resolve?.alias as Record<string, string> | undefined),
          "@smarter/common": COMMON_SRC,
          "@": path.join(packageDir, "src"),
        },
      },
    }),
  };
}
