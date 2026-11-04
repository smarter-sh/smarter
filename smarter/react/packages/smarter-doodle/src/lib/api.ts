/**
 * The doodle api. The sign-in page's visitor isn't signed in, so this is a plain, public GET,
 * without the CSRF or session headers of fetchDjangoUrl.
 */
import type { DoodleApiResponse } from "./Types";

/**
 * The browser's IANA time zone, e.g. Asia/Kolkata, which picks the visitor's region and date.
 *
 * @returns The time zone, or an empty string if the browser doesn't say.
 */
export function browserTimeZone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "";
  } catch {
    return "";
  }
}

/**
 * Fetch the doodle of the day.
 *
 * @param apiUrl The url of GET /api/v1/doodles/today/.
 * @param timeZone The visitor's time zone.
 * @param signal Aborts the request, e.g. when the component unmounts.
 * @returns The doodle of the day.
 * @throws Error If the request fails.
 */
export async function fetchDoodle(apiUrl: string, timeZone: string, signal?: AbortSignal): Promise<DoodleApiResponse> {
  const url = new URL(apiUrl, window.location.origin);
  if (timeZone) url.searchParams.set("tz", timeZone);
  const response = await fetch(url.toString(), { headers: { Accept: "application/json" }, signal });
  if (!response.ok) throw new Error(`GET ${url.pathname} failed: ${response.status}`);
  return (await response.json()) as DoodleApiResponse;
}
