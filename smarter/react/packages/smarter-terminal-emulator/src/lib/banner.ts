/**
 * What the terminal prints above the shell's prompt, and when the session ends: where the shell
 * runs, and why a session is a poor place for anything that must keep running.
 */
import { gettext, interpolate, ngettext } from "@smarter/common";

import type { ExitReason, SessionInfo } from "@/lib/session";

const YELLOW = "\x1b[33m";
const DIM = "\x1b[2m";
const BOLD = "\x1b[1m";
const RED = "\x1b[31m";
const RESET = "\x1b[0m";

/** A duration, in minutes below two hours, else in hours, e.g. "30 minutes" or "8 hours". */
export function duration(seconds: number): string {
  const minutes = Math.round(seconds / 60);
  if (minutes < 120) {
    return interpolate(ngettext("%(count)s minute", "%(count)s minutes", minutes), { count: minutes });
  }
  const hours = Math.round(minutes / 60);
  return interpolate(ngettext("%(count)s hour", "%(count)s hours", hours), { count: hours });
}

/** The banner, as terminal output: lines that end with \r\n, in color. */
export function banner(info: SessionInfo): string {
  const lines = [
    `${BOLD}${interpolate(gettext("Smarter Terminal: %(command)s on %(hostname)s, as %(user)s, pid %(pid)s."), {
      command: info.command,
      hostname: info.hostname,
      user: info.user,
      pid: info.pid,
    })}${RESET}`,
    "",
    gettext(
      "This shell runs inside the server process that accepted your connection: one of the platform's replicas, which the load balancer chose. Another window may open on another replica.",
    ),
    "",
    `${YELLOW}${gettext("This session can end suddenly, without warning:")}${RESET}`,
    `  • ${gettext("when the server restarts, or is redeployed or scaled down,")}`,
    `  • ${gettext("when your connection drops, or you reload or leave this page,")}`,
    `  • ${interpolate(gettext("after %(idle)s without input, and after %(max)s in any case."), {
      idle: duration(info.idle_timeout),
      max: duration(info.max_duration),
    })}`,
    "",
    `${YELLOW}${gettext("When it ends, everything that it started is stopped, so it is a poor place for long-running processes. Files that it writes may disappear when the container is replaced.")}${RESET}`,
    `${DIM}${gettext("The shell has the server's environment, and every one of its credentials.")}${RESET}`,
    "",
  ];
  return lines.join("\r\n") + "\r\n";
}

/** What the terminal prints below a screen that it redrew after the page was reloaded, or left and opened again. */
export function restored(): string {
  return `${RESET}\r\n${DIM}${gettext("Restored from before this page was left. That shell has ended, and a new one starts below.")}${RESET}\r\n\r\n`;
}

/** What the terminal prints when the session ends. */
export function ended(reason: ExitReason, code: number | null): string {
  const reasons: Record<ExitReason, string> = {
    exited: interpolate(gettext("The shell exited with status %(code)s."), { code: code ?? "?" }),
    idle: gettext("The session ended after too long without input."),
    expired: gettext("The session reached its time limit."),
    failed: gettext("The server could not start a shell."),
    refused: gettext(
      "The server refused the connection. The terminal may be disabled, or your sign-in may have expired.",
    ),
    disconnected: gettext("The connection to the server closed, and the session ended."),
  };
  const color = reason === "exited" ? DIM : RED;
  return `\r\n${color}${reasons[reason]}${RESET}\r\n${gettext("Press Enter to start a new session.")}\r\n`;
}
