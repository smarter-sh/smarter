/**
 * The user menu's requests to the console's account api, /api/web/account/: the user profile apis, which
 * return JSON, and the profile image api, which takes a multipart form, or a DELETE.
 */
import { fetchDjangoUrl, getCookie, gettext, interpolate, type SessionContext } from "@smarter/common";

import type { ProfileImageApiResponse, UserProfilesApiResponse } from "./Types";

/** The user profile apis' response, or their error message, else their status. */
async function userProfilesResponse(response: Response): Promise<UserProfilesApiResponse> {
  const data = (await response.json().catch(() => ({}))) as Partial<UserProfilesApiResponse> & { error?: string };
  if (!response.ok) {
    throw new Error(data.error || interpolate(gettext("Request failed: %(status)s"), { status: response.status }));
  }
  return data as UserProfilesApiResponse;
}

/**
 * GET the user's profiles, and which one the console acts as.
 *
 * @param url - The user profiles api's url.
 * @returns The user's profiles.
 * @throws Error with the api's error message, if it answers with one, else its status.
 */
export async function getUserProfiles(url: string): Promise<UserProfilesApiResponse> {
  const response = await fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } });
  return userProfilesResponse(response);
}

/**
 * POST a JSON body to one of the user profile apis.
 *
 * @param sessionContext - The cookies and headers of the request.
 * @param url - The api's url.
 * @param body - The request body.
 * @returns The user's profiles.
 * @throws Error with the api's error message, if it answers with one, else its status.
 */
export async function postUserProfiles(
  sessionContext: SessionContext,
  url: string,
  body: object = {},
): Promise<UserProfilesApiResponse> {
  const response = await fetchDjangoUrl(sessionContext, url, JSON.stringify(body));
  return userProfilesResponse(response);
}

/**
 * Sign out, with the console's account api.
 *
 * @param sessionContext - The cookies and headers of the request.
 * @param url - The sign-out api's url, /api/web/account/logout/.
 * @throws Error with the response's status, if it fails.
 */
export async function signOut(sessionContext: SessionContext, url: string): Promise<void> {
  const response = await fetchDjangoUrl(sessionContext, url, "{}");
  if (!response.ok) {
    throw new Error(interpolate(gettext("Request failed: %(status)s"), { status: response.status }));
  }
}

/**
 * Upload (POST, with a form whose profile_image is the file) or remove (DELETE) the user's profile image.
 *
 * @param sessionContext - The cookies of the request.
 * @param url - The profile image api's url.
 * @param method - POST or DELETE.
 * @param body - The form to upload, for a POST.
 * @returns The url of the image that the console shows now.
 * @throws Error with the api's validation messages, if any.
 */
export async function sendProfileImage(
  sessionContext: SessionContext,
  url: string,
  method: "POST" | "DELETE",
  body?: FormData,
): Promise<string> {
  const csrfToken = getCookie({ name: sessionContext.csrfCookieName, domain: sessionContext.cookieDomain }) || "";
  const response = await fetch(url, {
    method,
    body,
    headers: { "X-CSRFToken": csrfToken },
    credentials: "same-origin",
  });
  const data = (await response.json().catch(() => ({}))) as ProfileImageApiResponse;
  if (!response.ok || !data.profile_image_url) {
    const errors = data.profile_image || [data.error || gettext("The profile image could not be saved.")];
    throw new Error(errors.join(" "));
  }
  return data.profile_image_url;
}
