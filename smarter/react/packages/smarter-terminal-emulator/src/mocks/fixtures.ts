/** Example data for the terminal: its session context, a ticket, and the server's messages. See smarter.apps.dashboard.views.terminal_emulator. */
import type { SessionContext } from "@smarter/common";

import type { SessionInfo } from "@/lib/session";

export const TICKET_URL = "/dashboard/terminal/api/ticket/";
export const WEBSOCKET_PATH = "/ws/terminal/";

export const sessionContext: SessionContext = {
  ApiUrl: TICKET_URL,
  csrfCookieName: "csrftoken",
  djangoSessionCookieName: "sessionid",
  cookieDomain: "localhost",
  debugMode: false,
  smarterClient: "@smarter/terminal-emulator",
  smarterClientVersion: "0.0.0",
  smarterRequestId: "0123456789abcdef0123456789abcdef",
  smarterCapabilities: ["terminal"],
};

export const ticket = { ticket: "a-single-use-ticket", url: WEBSOCKET_PATH };

export const sessionInfo: SessionInfo = {
  hostname: "smarter-app-7d9f8c6b5-x2kqp",
  user: "smarter_user",
  command: "bash --login",
  pid: 4242,
  idle_timeout: 30 * 60,
  max_duration: 8 * 60 * 60,
};

export const sessionMessage = { type: "session", ...sessionInfo };

export const prompt = "\x1b[32msmarter_user@smarter-app\x1b[0m:\x1b[34m~\x1b[0m$ ";
