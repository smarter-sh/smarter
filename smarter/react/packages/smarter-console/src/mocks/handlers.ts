/** MSW handlers of the console's backend calls, for the stories and tests. */
import { http, HttpResponse } from "msw";

import type { ConsoleSession } from "@/contract.gen";
import { SESSION_API_URL } from "@/lib/const";
import { userSession, visitorSession } from "@/mocks/fixtures";

/** GET /api/web/session/ answers with this session. */
export function sessionHandler(session: ConsoleSession) {
  return http.get(SESSION_API_URL, () => HttpResponse.json(session));
}

export const userSessionHandler = sessionHandler(userSession);
export const visitorSessionHandler = sessionHandler(visitorSession);

/** GET /api/web/session/ fails. */
export const sessionErrorHandler = http.get(SESSION_API_URL, () =>
  HttpResponse.json({ error: "Server error" }, { status: 500 }),
);

/** The account api answers with this session after signing in, out or up. */
export function accountSessionHandler(url: string, session: ConsoleSession) {
  return http.post(url, () => HttpResponse.json(session));
}

/** The account api refuses with these errors and status. */
export function accountErrorsHandler(
  url: string,
  detail: string,
  fieldErrors: Record<string, string[]> = {},
  status = 400,
) {
  return http.post(url, () => HttpResponse.json({ detail, fieldErrors }, { status }));
}
