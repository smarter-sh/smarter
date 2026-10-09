import { loggerPrefix } from "./const";
import type { ListPage, ListQuery, Pagination, SessionContext } from "./Types";
import fetchDjangoUrl from "./django";
import { setCookieForUrl } from "../components/TabbedListView/cookie";

type LoadApiResponse<TObject> = {
  objects: TObject[];
  pagination?: Pagination;
  error?: string;
};

const getUrlOrigin = (): string => {
  if (typeof window !== "undefined" && typeof window.location?.origin === "string") {
    return window.location.origin;
  }
  return "http://localhost";
};

const buildLoadUrl = (apiUrl: string, urlSlug: string, invalidateCacheFlag: boolean, query: ListQuery = {}): string => {
  const origin = getUrlOrigin();
  const isAbsoluteApiUrl = /^[a-zA-Z][a-zA-Z\d+\-.]*:/.test(apiUrl);
  const normalizedBase = apiUrl.endsWith("/") ? apiUrl : `${apiUrl}/`;
  const normalizedSlug = urlSlug.replace(/^\/+|\/+$/g, "");
  const url = new URL(`${normalizedSlug}/`, new URL(normalizedBase, origin));
  url.searchParams.set("invalidate_cache", String(invalidateCacheFlag));
  if (query.page !== undefined) url.searchParams.set("page", String(query.page));
  if (query.pageSize !== undefined) url.searchParams.set("page_size", String(query.pageSize));
  const search = query.search?.trim();
  if (search) url.searchParams.set("search", search);

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
 * Loads a page of a list api's objects from the backend.
 *
 * @param sessionContext - Authentication and API context used for the request.
 * @param invalidateCacheFlag - If true, forces the backend to invalidate its cache.
 * @param urlSlug - The API slug for the API group (e.g., "owned" or "shared").
 * @param onError - Called with null before the request, and with the error message if it fails.
 * @param query - The page, page size and search to request. The api's defaults apply to those omitted.
 * @returns The page's objects and its pagination, or no objects if the request fails.
 */
export const load = async <TObject,>(
  sessionContext: SessionContext,
  invalidateCacheFlag: boolean,
  urlSlug: string,
  onError: (error: string | null) => void,
  query: ListQuery = {},
): Promise<ListPage<TObject>> => {
  onError(null);

  try {
    const url = buildLoadUrl(sessionContext.ApiUrl, urlSlug, invalidateCacheFlag, query);
    const response = await fetchDjangoUrl(sessionContext, url, JSON.stringify({}));

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
    setCookieForUrl(sessionContext.ApiUrl + urlSlug + "/", payload.objects.length, 7);
    return { objects: payload.objects, pagination: payload.pagination ?? null };
  } catch (error) {
    console.error(loggerPrefix, "load(): Error loading objects:", error);
    onError(error instanceof Error ? error.message : "Unable to load objects.");
    return { objects: [], pagination: null };
  }
};
