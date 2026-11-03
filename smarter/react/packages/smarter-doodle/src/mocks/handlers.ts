/**
 * MSW request handlers for the doodle api. Stories and tests use them to answer its requests. See
 * storybook/preview.ts and test/server.ts in the workspace.
 */
import { http, HttpResponse } from "msw";

import { appContext, diwali, quietDay } from "./fixtures";

export const diwaliHandler = http.get(appContext.apiUrl, () => HttpResponse.json(diwali));
export const quietDayHandler = http.get(appContext.apiUrl, () => HttpResponse.json(quietDay));
export const failingHandler = http.get(appContext.apiUrl, () => new HttpResponse(null, { status: 500 }));
