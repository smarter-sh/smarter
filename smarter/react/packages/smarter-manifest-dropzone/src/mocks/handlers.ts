/** MSW request handlers for the apply api. See storybook/preview.ts and test/server.ts in the workspace. */
import { http, HttpResponse } from "msw";

import { API_URL, applyResult } from "./fixtures";

export const applyHandlers = [http.post(API_URL, () => HttpResponse.json(applyResult))];

export const applyErrorHandlers = [
  http.post(API_URL, () => HttpResponse.json({ error: "Invalid manifest" }, { status: 400 })),
];
