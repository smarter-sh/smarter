
import { loggerPrefix } from "@/const";

/**
 * Sets a cookie to store the plugin count for a given URL slug.
 *
 * @param urlSlug - The unique identifier for the plugin group.
 * @param pluginCount - The number of plugins to store.
 * @param days - Number of days until the cookie expires.
 */
export const setCookie = (urlSlug: string, concept: string, pluginCount: number, days: number) => {
  const MS_PER_DAY = 24 * 60 * 60 * 1000;
  const expires = new Date(Date.now() + days * MS_PER_DAY).toUTCString();
  const cookieValue = `${urlSlug}_${concept}_plugin_count=${pluginCount}; path=/; expires=${expires};`;
  try {
    document.cookie = cookieValue;
    console.debug(loggerPrefix, `setCookie(): ${cookieValue}`);
  } catch (e) {
    console.warn(loggerPrefix, "setCookie(): Unable to set plugin count cookie", e);
  }
};

/**
 * Retrieves the plugin count stored in a cookie for a given URL slug.
 *
 * @param urlSlug - The unique identifier for the plugin group.
 * @returns The number of plugins stored in the cookie, or undefined if not found or invalid.
 */
export const getCookie = (urlSlug: string, concept: string): number | undefined => {
  const cookieName = `${urlSlug}_${concept}_plugin_count`;
  const cookies = document.cookie.split(";").map((c) => c.trim());
  for (const cookie of cookies) {
    if (cookie.startsWith(cookieName + "=")) {
      const strVal = cookie.substring(cookieName.length + 1);
      const numVal = parseInt(strVal, 10);
      const retVal = isNaN(numVal) ? undefined : numVal;
      console.debug(loggerPrefix, `getCookie(): Retrieved cookie for ${cookieName}:`, retVal);
      return retVal;
    }
  }
  console.warn(
    loggerPrefix,
    `getCookie(): Cookie for ${cookieName} not found. If you are not under /, it may not be visible due to cookie path restrictions.`,
  );
  return undefined;
};
