import { loggerPrefix } from "../../lib/const";
import type { SessionContext } from "../../lib/Types";
import fetchDjangoUrl from "../../lib/django";
import { setCookie } from "./cookie";

type LoadApiResponse<TObject> = {
  objects: TObject[];
  error?: string;
};

const getUrlOrigin = (): string => {
  if (typeof window !== "undefined" && typeof window.location?.origin === "string") {
    return window.location.origin;
  }
  return "http://localhost";
};

const buildLoadUrl = (apiUrl: string, urlSlug: string, invalidateCacheFlag: boolean): string => {
  const origin = getUrlOrigin();
  const isAbsoluteApiUrl = /^[a-zA-Z][a-zA-Z\d+\-.]*:/.test(apiUrl);
  const normalizedBase = apiUrl.endsWith("/") ? apiUrl : `${apiUrl}/`;
  const normalizedSlug = urlSlug.replace(/^\/+|\/+$/g, "");
  const url = new URL(`${normalizedSlug}/`, new URL(normalizedBase, origin));
  url.searchParams.set("invalidate_cache", String(invalidateCacheFlag));

  if (isAbsoluteApiUrl) {
    return url.toString();
  }

  return `${url.pathname}${url.search}${url.hash}`;
};

const readJsonSafely = async (response: Response): Promise<unknown | null> => {
  try {
    return await response.json();
  } catch {
    return null;
  }
};

const getErrorMessage = (status: number, responseBody: unknown): string => {
  if (
    typeof responseBody === "object" &&
    responseBody !== null &&
    "error" in responseBody &&
    typeof responseBody.error === "string" &&
    responseBody.error.trim().length > 0
  ) {
    return responseBody.error;
  }

  return `Failed to load objects (${status})`;
};

/**
 * Loads chatbot data from the backend API and updates state.
 *
 * @param setterCallback - State setter for updating the chatbot list.
 * @param setLoading - State setter for loading state.
 * @param urlSlug - The API slug for the chatbot group (e.g., "owned" or "shared").
 * @param invalidateCache - If true, forces the backend to invalidate its cache (default: false).
 */
export const load = async <TObject,>(
  sessionContext: SessionContext<TObject>,
  invalidateCacheFlag: boolean,
  setLoading: React.Dispatch<React.SetStateAction<boolean>>,
  urlSlug: string,
  onError: (error: string | null) => void,
): Promise<TObject[]> => {
  setLoading(true);
  onError(null);

  try {
    const url = buildLoadUrl(sessionContext.ApiUrl, urlSlug, invalidateCacheFlag);
    const response = await fetchDjangoUrl(
      JSON.stringify({}),
      url,
      sessionContext.djangoSessionCookieName,
      sessionContext.csrfCookieName,
      sessionContext.cookieDomain,
    );

    const responseBody = await readJsonSafely(response);

    if (!response.ok) {
      throw new Error(getErrorMessage(response.status, responseBody));
    }

    if (
      typeof responseBody !== "object" ||
      responseBody === null ||
      !("objects" in responseBody) ||
      !Array.isArray(responseBody.objects)
    ) {
      throw new Error("Invalid response payload: expected objects array.");
    }

    const payload = responseBody as LoadApiResponse<TObject>;
    setCookie(sessionContext.ApiUrl + urlSlug + "/", payload.objects.length, 7);
    return payload.objects;
  } catch (error) {
    console.error(loggerPrefix, "load(): Error loading objects:", error);
    onError(error instanceof Error ? error.message : "Unable to load objects.");
    return [];
  } finally {
    setLoading(false);
  }
};
