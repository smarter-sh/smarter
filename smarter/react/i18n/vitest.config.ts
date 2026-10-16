/**
 * Tests of the message extractor, i18n/extract.ts. They run in Node, not jsdom.
 */
import { defineProject } from "vitest/config";

export default defineProject({
  test: {
    name: "i18n",
    root: import.meta.dirname,
    environment: "node",
    include: ["*.test.ts"],
  },
});
