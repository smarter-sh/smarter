/**
 * The user menu's requests to Django: the user profile apis, which take and return JSON, and the
 * profile image api, which takes a multipart form, or a DELETE.
 */
import { fetchDjangoUrl, getCookie, gettext, interpolate, type SessionContext } from "@smarter/common";

import type { ProfileImageApiResponse, UserProfilesApiResponse } from "./Types";

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
  const data = (await response.json().catch(() => ({}))) as Partial<UserProfilesApiResponse> & { error?: string };
  if (!response.ok) {
    throw new Error(data.error || interpolate(gettext("Request failed: %(status)s"), { status: response.status }));
  }
  return data as UserProfilesApiResponse;
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
