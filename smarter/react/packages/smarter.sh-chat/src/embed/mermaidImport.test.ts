import { pathToFileURL } from "node:url";
import { afterEach, describe, expect, it } from "vitest";

import { captureBaseUrl } from "./assets";
import { importMermaid } from "./mermaidImport";

describe("the embed's mermaid import", () => {
  afterEach(() => {
    captureBaseUrl(null);
  });

  it("imports the separate build of mermaid from embed/mermaid/, beside the script", async () => {
    // __fixtures__/embed/mermaid/mermaid.js stands in for the build.
    const script = document.createElement("script");
    script.src = pathToFileURL(`${import.meta.dirname}/__fixtures__/embed.js`).toString();
    captureBaseUrl(script);
    const mermaid = await importMermaid();
    expect(mermaid.default).toEqual({ fake: true });
  });
});
