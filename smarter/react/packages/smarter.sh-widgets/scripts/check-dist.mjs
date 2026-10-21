/**
 * Checks the built npm package in dist/, before it is published: `npm run check:dist`, after `npm run build:lib`.
 * The react job in .github/workflows/test.yml and .github/workflows/uiWidgetsRelease.yml run it.
 *
 * - every file that package.json's exports and fields name exists,
 * - the library imports only React and its own stylesheet, so @smarter/common, which is not on npm, is bundled,
 * - the library uses React's production JSX runtime, whatever NODE_ENV the build ran with,
 * - dist/ has none of the Keen theme's files: its stylesheet and images stay with the pages that serve them,
 * - the library is within its size budget,
 * - the library works: rendered on the server, each widget renders its labelled card.
 */
import fs from "node:fs";
import path from "node:path";
import { gzipSync } from "node:zlib";
import { pathToFileURL } from "node:url";

const root = path.resolve(import.meta.dirname, "..");
const dist = path.join(root, "dist");
const pkg = JSON.parse(fs.readFileSync(path.join(root, "package.json"), "utf-8"));
const library = path.join(root, pkg.module);
// gzipped. The library is about 20 kB today: ten widgets, their inlined logos, and gettext().
const BUDGET_BYTES = 50_000;
const ALLOWED_IMPORTS = new Set(["react", "react/jsx-runtime", "./ui-widgets.css"]);

const failures = [];
const check = (ok, message) => {
  console.log(`${ok ? "ok:  " : "FAIL:"} ${message}`);
  if (!ok) failures.push(message);
};

// files that package.json names.
const named = new Set([pkg.main, pkg.module, pkg.types]);
for (const target of Object.values(pkg.exports)) {
  for (const file of typeof target === "string" ? [target] : Object.values(target)) named.add(file);
}
for (const file of [...named].filter(Boolean)) {
  check(fs.existsSync(path.join(root, file)), `${file} exists`);
}

// the library's imports.
const source = fs.existsSync(library) ? fs.readFileSync(library, "utf-8") : "";
const imports = [...source.matchAll(/^import\s+(?:[^"']*\s+from\s+)?["']([^"']+)["']/gm)].map((m) => m[1]);
const unexpected = imports.filter((name) => !ALLOWED_IMPORTS.has(name));
check(
  unexpected.length === 0,
  `the library imports only React and its stylesheet (${[...new Set(imports)].join(", ")})`,
);
check(imports.includes("./ui-widgets.css"), "the library imports ./ui-widgets.css");
check(!/jsxDEV|jsx-dev-runtime/.test(source), "the library uses React's production JSX runtime");

// none of the Keen theme's files.
const files = fs.existsSync(dist) ? fs.readdirSync(dist, { recursive: true }).map(String) : [];
const keen = files.filter((name) => /\.(png|jpe?g|gif|woff2?|ttf|eot)$/i.test(name) || /bundle\.css$/.test(name));
check(keen.length === 0, `dist/ has no theme images, fonts or bundles${keen.length ? `: ${keen.join(", ")}` : ""}`);

// size.
const gzipped = gzipSync(source).length;
check(gzipped > 0 && gzipped <= BUDGET_BYTES, `the library is ${gzipped} bytes gzipped (budget ${BUDGET_BYTES})`);

// the library works. Node can't import a stylesheet, so a copy without that import is rendered, next to the
// original, so that it resolves react from this workspace.
if (source) {
  const copy = path.join(dist, `.check-dist-${process.pid}.mjs`);
  fs.writeFileSync(copy, source.replace(/^import\s+["']\.\/ui-widgets\.css["'];?\s*$/m, ""));
  try {
    const widgets = await import(pathToFileURL(copy).href);
    const { createElement } = await import("react");
    const { renderToStaticMarkup } = await import("react-dom/server");
    const names = Object.keys(widgets).sort();
    check(names.length >= 10, `the library exports its widgets (${names.join(", ")})`);
    for (const name of names) {
      // every widget is a card in a labelled <section>, or <div> (VSCodeExtension). React puts its image
      // preload <link>s first.
      const html = renderToStaticMarkup(createElement(widgets[name]));
      check(/<(section|div) [^>]*aria-label="[^"]+"/.test(html), `${name} renders its labelled card`);
    }
  } finally {
    fs.rmSync(copy, { force: true });
  }
}

if (failures.length) {
  console.error(`\n${failures.length} check(s) failed.`);
  process.exit(1);
}
console.log("\nThe package is ready to publish.");
