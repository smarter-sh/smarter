import { loggerPrefix } from "../../lib/const";
import { packageName, packageVersion } from "../../lib/const";

const COOKIE_NAME_PREFIX = `${packageName}_v${packageVersion}`;
export const getUrlPath = (url: string): string => {
  return new URL(url).pathname;
};

/**
 * Sets a cookie to store the chatbot count for a given URL.
 *
 * @param url - The unique identifier for the chatbot group.
 * @param chatbotCount - The number of chatbots to store.
 * @param days - Number of days until the cookie expires.
 */
export const setCookie = (url: string, chatbotCount: number, days: number) => {
  const MS_PER_DAY = 24 * 60 * 60 * 1000;
  const expires = new Date(Date.now() + days * MS_PER_DAY).toUTCString();
  const cookieValue = `${COOKIE_NAME_PREFIX}_${getUrlPath(url)}=${chatbotCount}; path=/; expires=${expires};`;
  try {
    document.cookie = cookieValue;
    console.debug(loggerPrefix, `setCookie(): ${cookieValue}`);
  } catch (e) {
    console.warn(loggerPrefix, "setCookie(): Unable to set chatbot count cookie", e);
  }
};

/**
 * Retrieves the chatbot count stored in a cookie for a given URL.
 *
 * @param url - The unique identifier for the chatbot group.
 * @returns The number of chatbots stored in the cookie, or undefined if not found or invalid.
 */
export const getCookie = (url: string): number | undefined => {
  const cookieName = `${COOKIE_NAME_PREFIX}_${getUrlPath(url)}`;
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
