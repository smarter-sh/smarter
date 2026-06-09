import type { SessionContext } from "@smarter/common";

import { loggerPrefix } from "@/const";
import type { LLMClient, UserProfile } from "@/lib/Types";
import fetchDjangoUrl from "@/lib/django";
import { setCookie } from "./cookie";

interface ApiResponse {
  user: UserProfile;
  admin: UserProfile;
  objects: LLMClient[];
}

/**
 * Loads llm_client data from the backend API and updates state.
 *
 * @param setterCallback - State setter for updating the llm_client list.
 * @param setLoading - State setter for loading state.
 * @param urlSlug - The API slug for the llm_client group (e.g., "owned" or "shared").
 * @param invalidateCache - If true, forces the backend to invalidate its cache (default: false).
 */
export const load = async (
  sessionContext: SessionContext,
  invalidateCacheFlag: boolean,
  setLoading: React.Dispatch<React.SetStateAction<boolean>>,
  urlSlug: string,
  onError: (error: string | null) => void,
): Promise<LLMClient[]> => {
  setLoading(true);
  onError(null);

  try {
    let base = sessionContext.ApiUrl;
    if (!base.endsWith("/")) base += "/";
    let slug = urlSlug.startsWith("/") ? urlSlug.slice(1) : urlSlug;
    let url = base + slug;
    if (!url.endsWith("/")) url += "/";
    url += `?invalidate_cache=${invalidateCacheFlag}`;
    const response = await fetchDjangoUrl(
      JSON.stringify({}),
      url,
      sessionContext.djangoSessionCookieName,
      sessionContext.csrfCookieName,
      sessionContext.cookieDomain,
    );

    if (!response.ok) {
      let errorMsg = `Failed to load objects (${response.status})`;
      try {
        const errorJson = await response.json();
        if (errorJson && errorJson.error) {
          errorMsg = errorJson.error;
        }
      } catch {
        console.error(loggerPrefix, "load(): Failed to load objects due to an unknown error.");
      }
      throw new Error(errorMsg);
    }

    const payload = (await response.json()) as ApiResponse;
    setCookie(urlSlug, "llm_client_count", payload.objects.length, 7);
    return payload.objects;
  } catch (error) {
    console.error(loggerPrefix, "load(): Error loading objects:", error);
    onError(error instanceof Error ? error.message : "Unable to load objects.");
    return [];
  } finally {
    setLoading(false);
  }
};
