/** MSW request handlers for the passthrough api. See storybook/preview.ts and test/server.ts in the workspace. */
import { http, HttpResponse } from "msw";

import { API_URL, PROVIDER_API_URL, completion, providers } from "./fixtures";

export const providerHandlers = [http.post(PROVIDER_API_URL, () => HttpResponse.json({ providers }))];

/** A prompt to any provider succeeds. */
export const passthroughHandlers = [
  ...providerHandlers,
  http.post(`${API_URL}:provider/`, () => HttpResponse.json(completion)),
];

/** The provider rejects the prompt. */
export const passthroughErrorHandlers = [
  ...providerHandlers,
  http.post(`${API_URL}:provider/`, () =>
    HttpResponse.json({ error: { message: "Invalid API key" } }, { status: 401 }),
  ),
];
