/**
 * Vitest setup for Smarter Chat. See vitest.config.ts.
 *
 * - Adds jest-dom's matchers, e.g. expect(element).toBeInTheDocument().
 * - Starts the MSW server (test/server.ts), which fails any test that makes an unmocked request.
 * - Resolves relative fetch() URLs against the page, as browsers do. Node's fetch() rejects
 *   them, and the apps request relative URLs, e.g. /workbench/llm-clients/<hashed_id>/config/.
 * - Applies the shared Storybook parameters to the stories that the tests render.
 * - Puts the chat back into English after each test, which the tests assert. See src/lib/i18n.tsx.

 */
import "@testing-library/jest-dom/vitest";

import { setProjectAnnotations } from "@storybook/react-vite";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll } from "vitest";

import { activateLanguage } from "@/lib/i18n";
import { sharedParameters } from "../.storybook/parameters";
import { server } from "./server";

setProjectAnnotations([{ parameters: sharedParameters }]);

const nodeFetch = globalThis.fetch;
globalThis.fetch = (input: RequestInfo | URL, init?: RequestInit) =>
  nodeFetch(typeof input === "string" ? new URL(input, window.location.href) : input, init);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  cleanup();
  server.resetHandlers();
  window.sessionStorage.clear();
  window.localStorage.clear();
  // English, which the tests assert, unless a test asks for another language.
  document.documentElement.lang = "";
  activateLanguage();

  for (const cookie of document.cookie.split(";")) {
    document.cookie = `${cookie.split("=")[0].trim()}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
  }
});
afterAll(() => server.close());
