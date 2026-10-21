/**
 * Checks the built npm package in dist/, before it is published: `npm run check:dist`, after `npm run build:lib` and
 * `npm run build:embed`. The GitHub build and release workflows run it (.github/actions/build-package).
 *
 * - every file that package.json's exports and fields name exists,
 * - the embed script's own files are beside it: embed/mermaid/mermaid.js and KaTeX's woff2 fonts,
 * - the embed script is React's production build, and is within its size budget,
 * - the embed script works: loaded into a page (jsdom), it defines <smarter-chat>, sets window.SmarterChat with this
 *   package's version, and adds a launcher, with its css in a shadow root, for its script tag's data-chatbot.
 *
 * The launcher isn't opened, so the check makes no request to a Smarter platform.
 */
import fs from "node:fs";
import path from "node:path";
import { gzipSync } from "node:zlib";
import { pathToFileURL } from "node:url";
import { JSDOM } from "jsdom";

const root = path.resolve(import.meta.dirname, "..");
const dist = path.join(root, "dist");
const pkg = JSON.parse(fs.readFileSync(path.join(root, "package.json"), "utf-8"));
// gzipped. The embed script is about 330 kB today: React, React DOM, the chat and its css.
const EMBED_BUDGET_BYTES = 400_000;

const failures = [];
const check = (ok, message) => {
  console.log(`${ok ? "ok:  " : "FAIL:"} ${message}`);
  if (!ok) failures.push(message);
};

// files that package.json names.
const exported = new Set([pkg.main, pkg.module, pkg.types, pkg.jsdelivr, pkg.unpkg]);
for (const target of Object.values(pkg.exports)) {
  for (const file of typeof target === "string" ? [target] : Object.values(target)) exported.add(file);
}
for (const file of [...exported].filter(Boolean)) {
  check(fs.existsSync(path.join(root, file)), `${file} exists`);
}

// the embed script's own files.
const embed = path.join(dist, "embed.js");
check(fs.existsSync(path.join(dist, "embed/mermaid/mermaid.js")), "dist/embed/mermaid/mermaid.js exists");
const fonts = fs.existsSync(path.join(dist, "embed/katex/fonts"))
  ? fs.readdirSync(path.join(dist, "embed/katex/fonts")).filter((name) => name.endsWith(".woff2"))
  : [];
check(fonts.length >= 20, `dist/embed/katex/fonts/ has KaTeX's woff2 fonts (${fonts.length})`);

const source = fs.existsSync(embed) ? fs.readFileSync(embed, "utf-8") : "";
const gzipped = gzipSync(source).length;
check(
  gzipped > 0 && gzipped <= EMBED_BUDGET_BYTES,
  `embed.js is ${Math.round(gzipped / 1000)} kB gzipped (budget ${EMBED_BUDGET_BYTES / 1000} kB)`,
);
// React's production build replaces its error messages with links to react.dev/errors; the development build doesn't.
check(source.includes("react.dev/errors/"), "embed.js is React's production build");
check(!/\bprocess\.env\.NODE_ENV\b/.test(source), "embed.js has no process.env.NODE_ENV for a page to trip on");

// the embed script, in a page.
const page = new JSDOM(
  `<!doctype html><html><head></head><body>
     <script src="embed.js" data-chatbot="https://docs-bot.example.com/" data-label="Ask us"></script>
   </body></html>`,
  { url: pathToFileURL(path.join(dist, "index.html")).href, runScripts: "dangerously", resources: "usable" },
);
await new Promise((resolve) => {
  page.window.addEventListener("load", resolve);
  setTimeout(resolve, 10_000);
});
const { window } = page;
check(!!window.customElements.get("smarter-chat"), "the embed script defines <smarter-chat>");
check(
  window.SmarterChat?.version === pkg.version,
  `window.SmarterChat.version is ${pkg.version} (${window.SmarterChat?.version})`,
);
const launcher = window.document.querySelector("smarter-chat");
check(launcher?.getAttribute("mode") === "launcher", "the script tag added a launcher");
await new Promise((resolve) => setTimeout(resolve, 100));
const shadow = launcher?.shadowRoot;
check(!!shadow?.querySelector("button[aria-label='Ask us']"), "the launcher's button is in its shadow root");
check(
  (shadow?.querySelector("style")?.textContent ?? "").includes(".SmarterChat"),
  "the chat's css is in the shadow root",
);
check(!window.document.head.querySelector("style:not(#smarter-chat-embed-fonts)"), "no css leaks into the page's head");
window.close();

if (failures.length) {
  console.error(`\n${failures.length} check(s) failed.`);
  process.exit(1);
}
console.log("\nThe package is ready to publish.");
