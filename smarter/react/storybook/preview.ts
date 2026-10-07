/**
 * Shared Storybook preview for every package in this workspace. Each package's
 * .storybook/preview.ts re-exports it.
 *
 * API mocking: a story declares the API responses that it needs as MSW request handlers, in
 * parameters.msw.handlers:
 *
 *     export const Default: Story = {
 *       parameters: { msw: { handlers: [http.post("/secret/api/listview/owned/", () => HttpResponse.json(...))] } },
 *     };
 *
 * In Storybook, MSW's service worker answers those requests. In the Vitest tests, which render
 * every story (see test/stories.ts), MSW's Node server answers them, with the same handlers.
 */
import type { Preview } from "@storybook/react-vite";
import type { RequestHandler } from "msw";
import { setupWorker, type SetupWorker } from "msw/browser";

import { sharedParameters } from "./parameters";

let worker: SetupWorker | undefined;

/** Start MSW's service worker once, and give each story only its own request handlers. */
async function mswLoader({ parameters }: { parameters: { msw?: { handlers?: RequestHandler[] } } }) {
  if (!worker) {
    worker = setupWorker();
    await worker.start({ onUnhandledRequest: "bypass", quiet: true });
  }
  worker.resetHandlers(...(parameters.msw?.handlers ?? []));
  return {};
}

const preview: Preview = {
  parameters: sharedParameters,
  loaders: [mswLoader],
  tags: ["autodocs"],
};

export default preview;
