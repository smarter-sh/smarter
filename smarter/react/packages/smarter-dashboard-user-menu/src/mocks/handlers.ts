/**
 * MSW request handlers for the user profile and profile image endpoints of the console's account api. Stories and tests use them
 * to answer their requests. See storybook/preview.ts and test/server.ts in the workspace.
 */
import { http, HttpResponse } from "msw";

import { appContext, switchedUserProfiles, userProfiles } from "./fixtures";

export const userProfilesHandler = http.get(appContext.urls.userProfilesApi, () => HttpResponse.json(userProfiles));
export const userProfileSelectHandler = http.post(appContext.urls.userProfileSelectApi, () =>
  HttpResponse.json(switchedUserProfiles),
);

/** Both user profile apis. */
export const userProfileHandlers = [userProfilesHandler, userProfileSelectHandler];

/** The user profiles api fails. */
export const userProfilesErrorHandlers = [
  http.get(appContext.urls.userProfilesApi, () => HttpResponse.json({ error: "Service unavailable" }, { status: 503 })),
];

/** The account api signs the user out. */
export const signOutHandler = http.post(appContext.urls.logout, () => HttpResponse.json({ isAuthenticated: false }));

/** The account api refuses to sign the user out, e.g. without the CSRF token. */
export const signOutErrorHandler = http.post(appContext.urls.logout, () =>
  HttpResponse.json({ detail: "Forbidden" }, { status: 403 }),
);

/** The profile image api accepts an upload, and a removal. */
export const profileImageHandlers = [
  http.post(appContext.urls.profileImageApi, () =>
    HttpResponse.json({ profile_image_url: "https://example.com/media/profile-images/ada.png" }),
  ),
  http.delete(appContext.urls.profileImageApi, () =>
    HttpResponse.json({ profile_image_url: "http://localhost:9357/static/images/avatars/default-profile.svg" }),
  ),
];
