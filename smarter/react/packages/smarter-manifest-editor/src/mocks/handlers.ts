/** MSW request handlers for the smarter cli api. See storybook/preview.ts and test/server.ts in the workspace. */
import { http, HttpResponse } from "msw";

import { APPLY_API_URL, VALIDATE_API_URL } from "./fixtures";

export const validHandler = http.post(VALIDATE_API_URL, () => HttpResponse.json({ data: { valid: true, errors: [] } }));

/** The manifest's SAM model rejects spec.config.value. */
export const invalidHandler = http.post(VALIDATE_API_URL, () =>
  HttpResponse.json({
    data: {
      valid: false,
      errors: [{ loc: ["spec", "config", "value"], message: "value must be at least 32 characters" }],
    },
  }),
);

export const cliHandlers = [
  validHandler,
  http.post(APPLY_API_URL, () => HttpResponse.json({ message: "Secret example_secret applied" })),
  http.post("/api/v1/cli/delete/:kind/", () => HttpResponse.json({ message: "Secret example_secret deleted" })),
];
