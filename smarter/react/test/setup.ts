/**
 * Vitest setup for every package in this workspace. See vitest.shared.ts.
 *
 * - Adds jest-dom's matchers, e.g. expect(element).toBeInTheDocument().
 * - Starts the MSW server (test/server.ts), which fails any test that makes an unmocked request.
 * - Resolves relative fetch() URLs against the page, as browsers do. Node's fetch() rejects
 *   them, and the apps request relative URLs, e.g. /secret/react-integration/api/listview/.
 * - Applies the shared Storybook parameters to the stories that the tests render, and mounts them
 *   with Testing Library so that cleanup() unmounts them after each test.
 * - Gives waitFor() and findBy*() 5 seconds instead of 1. The CI runner runs 268 test files at once,
 *   and a mocked request or a re-render can take longer than a second there.
 */
import "@testing-library/jest-dom/vitest";

import { setProjectAnnotations } from "@storybook/react-vite";
import { cleanup, configure, render } from "@testing-library/react";
import { afterAll, afterEach, beforeAll } from "vitest";

import { sharedParameters } from "../storybook/parameters";
import { server } from "./server";

// testingLibraryRender makes the stories that testStories() runs mount with Testing Library, so
// cleanup() below unmounts each one. Storybook's own renderer unmounts a story only when the next
// one runs, which leaves a file's last story mounted after jsdom is torn down, and a late api
// response then fails the run with "window is not defined".
setProjectAnnotations([{ parameters: sharedParameters, testingLibraryRender: render }]);
configure({ asyncUtilTimeout: 5000 });

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
