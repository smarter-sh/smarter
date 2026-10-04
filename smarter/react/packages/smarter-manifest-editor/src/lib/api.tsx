/**
 * Calls to the Smarter cli api, which authenticates the user's Django session.
 *
 * The brokers behind it enforce the same rules as the cli, e.g. delete refuses a
 * resource that other resources depend on.
 */
import { fetchDjangoUrl } from "@smarter/common";
import type { SessionContext } from "@smarter/common";

import { loggerPrefix } from "@/const";

export type CliResult = {
  ok: boolean;
  message: string;
};

type CliResponseBody = {
  message?: string;
  data?: { message?: string } | unknown;
  error?: { description?: string; message?: string } | string;
};

function errorMessage(body: CliResponseBody | null, response: Response): string {
  const error = body?.error;
  if (typeof error === "string") return error;
  return error?.description || error?.message || `${response.status} ${response.statusText}`;
}

/** POST to a cli api url, and return whether it succeeded, with its message. */
export async function callCli(
  sessionContext: SessionContext,
  url: string,
  body: unknown,
  successMessage: string,
): Promise<CliResult> {
  const response = await fetchDjangoUrl(sessionContext, url, JSON.stringify(body ?? {}));
  const data = (await response.json().catch(() => null)) as CliResponseBody | null;
  console.debug(loggerPrefix, `callCli() ${url} returned ${response.status}:`, data);
  if (!response.ok) {
    return { ok: false, message: errorMessage(data, response) };
  }
  return { ok: true, message: data?.message || successMessage };
}
