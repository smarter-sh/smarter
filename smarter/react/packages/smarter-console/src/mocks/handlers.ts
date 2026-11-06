/** MSW handlers of the console's backend calls, for the stories and tests. */
import { http, HttpResponse } from "msw";

import type { ConsoleSession } from "@/contract.gen";
import { DOODLE_API_URL, SESSION_API_URL } from "@/lib/const";
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

/** GET /api/v1/doodles/today/ answers with a holiday's doodle. See smarter.apps.doodle.contract.models. */
export const doodleHandler = http.get(DOODLE_API_URL, () =>
  HttpResponse.json({
    date: "2026-11-08",
    region: "south-asia",
    theme: "diwali",
    title: "Diwali",
    caption: "Happy Diwali!",
    altText: "Glowing diyas line the ground below a Smarter LLMClient.",
    linkUrl: "https://en.wikipedia.org/wiki/Diwali",
    imageUrl: "/static/doodle/base.svg",
    isDefault: false,
    aiCredit: "",
    learnHowUrl: "https://docs.smarter.sh/",
    animated: false,
    showCaption: true,
  }),
);
