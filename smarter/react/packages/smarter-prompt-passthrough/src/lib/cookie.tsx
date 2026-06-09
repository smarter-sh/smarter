/**
 * Reads a cookie value from `document.cookie`, falling back to a default.
 *
 * If `cookie.value` is non-null, it is returned immediately without reading
 * the browser cookies. Otherwise the cookie is looked up by name, scoped to
 * the current hostname matching `cookie.domain`.
 *
 * @param cookie - Cookie descriptor object.
 * @param cookie.name - The cookie name to look up.
 * @param cookie.expiration - Unused in this function; present for shape consistency.
 * @param cookie.domain - Domain suffix the current hostname must match.
 * @param cookie.value - Pre-set value; returned directly if non-null.
 * @param defaultValue - Value returned when the cookie is not found. Defaults to `null`.
 * @returns The cookie value, or `defaultValue` if not found.
 */
export default function getCookie(cookie: { name: string; expiration: number | null; domain: string; value: string | null }, defaultValue: string | null = null) {
  if (cookie.value !== null) {
    return cookie.value;
  }
  let cookieValue = null;

  if (window.location.hostname.endsWith(cookie.domain) && document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";").map((cookie) => cookie.trim());
    for (let i = 0; i < cookies.length; i++) {
      const thisCookie = cookies[i];
      if (thisCookie.startsWith(`${cookie.name}=`)) {
        cookieValue = decodeURIComponent(thisCookie.substring(cookie.name.length + 1));
        break;
      }
    }
  }

  return cookieValue || defaultValue;
}

/**
 * Writes or clears a cookie in `document.cookie`.
 *
 * Passing a non-null `value` sets the cookie with an expiration calculated
 * from `cookie.expiration` (milliseconds from now). Passing `null` immediately
 * expires the cookie, effectively deleting it.
 *
 * @param cookie - Cookie descriptor object.
 * @param cookie.name - The cookie name to set.
 * @param cookie.expiration - Lifetime in milliseconds from the current time.
 * @param cookie.domain - Informational; not written to the cookie string here.
 * @param cookie.value - Unused in this function; present for shape consistency.
 * @param value - The value to store, or `null` to delete the cookie.
 */
export function setCookie(cookie: { name: string; expiration: number; domain: string; value: string | null }, value: string | null) {
  const currentPath = window.location.pathname;
  if (value) {
    const expirationDate = new Date();
    expirationDate.setTime(expirationDate.getTime() + cookie.expiration);
    const expires = expirationDate.toUTCString();
    const cookieData = `${cookie.name}=${value}; path=${currentPath}; SameSite=Lax; expires=${expires}`;
    document.cookie = cookieData;
  } else {
    // Unset the cookie by setting its expiration date to the past
    const expirationDate = new Date(0);
    const expires = expirationDate.toUTCString();
    const cookieData = `${cookie.name}=; path=${currentPath}; SameSite=Lax; expires=${expires}`;
    document.cookie = cookieData;
  }
}

/**
 * Creates a cookie descriptor object for use with {@link getCookie} and {@link setCookie}.
 *
 * @param cookieName - The cookie name.
 * @param cookieExpiration - Lifetime in milliseconds, or `null` for session cookies.
 * @param cookieDomain - Domain suffix used to scope cookie reads.
 * @param cookieValue - Pre-set value to bypass cookie lookup. Defaults to `null`.
 * @returns A cookie descriptor object.
 */
export function cookieMetaFactory(cookieName: string, cookieExpiration: number | null, cookieDomain: string, cookieValue: string | null = null) {
  /*
  Create a cookie object.
   */
  return {
    name: cookieName,
    expiration: cookieExpiration,
    domain: cookieDomain,
    value: cookieValue,
  };
}
