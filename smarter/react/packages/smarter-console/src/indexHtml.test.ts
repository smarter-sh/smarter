/**
 * The console's page, index.html, which Django serves at the console's paths. See
 * smarter.apps.dashboard.views.console_app.
 */
import fs from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

const html = fs.readFileSync(path.resolve(import.meta.dirname, "..", "index.html"), "utf-8");

describe("index.html", () => {
  it("loads the translation catalog before the console's own script", () => {
    // @smarter/common's gettext() reads window.django, which /jsi18n/ defines.
    const catalog = html.indexOf('src="/jsi18n/"');
    const app = html.indexOf('src="/src/main.tsx"');
    expect(catalog).toBeGreaterThan(-1);
    expect(app).toBeGreaterThan(catalog);
  });

  it("sets the theme's mode before the theme's stylesheets", () => {
    // the theme defines its colors and layout variables under [data-bs-theme=light] and [data-bs-theme=dark].
    const mode = html.indexOf('setAttribute("data-bs-theme"');
    const theme = html.indexOf("style.bundle.css");
    expect(mode).toBeGreaterThan(-1);
    expect(theme).toBeGreaterThan(mode);
  });

  it("has the root element that main.tsx mounts the console in", () => {
    expect(html).toContain('id="smarter-console-root"');
  });
});
