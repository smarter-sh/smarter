/**
 * Vitest setup for every package in this workspace. See vitest.shared.ts.
 *
 * - Adds jest-dom's matchers, e.g. expect(element).toBeInTheDocument().
 * - Starts the MSW server (test/server.ts), which fails any test that makes an unmocked request.
 * - Resolves relative fetch() URLs against the page, as browsers do. Node's fetch() rejects
 *   them, and the apps request relative URLs, e.g. /secret/react-integration/api/listview/.
 * - Applies the shared Storybook parameters to the stories that the tests render.
 */
import "@testing-library/jest-dom/vitest";

import { setProjectAnnotations } from "@storybook/react-vite";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll } from "vitest";

import { sharedParameters } from "../storybook/parameters";
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
  for (const cookie of document.cookie.split(";")) {
    document.cookie = `${cookie.split("=")[0].trim()}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
  }
});
afterAll(() => server.close());
