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
