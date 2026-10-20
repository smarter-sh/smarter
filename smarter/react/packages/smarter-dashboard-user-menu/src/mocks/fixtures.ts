/**
 * Example data for this package's stories and tests: the root element's attributes, and what the
 * Django user profile and profile image apis return. See templates/react/dashboard-user-menu.html,
 * smarter.apps.account.views.dashboard.user_profiles and smarter.apps.account.views.dashboard.profile_image.
 */
import type { SessionContext } from "@smarter/common";

import type { AppContext, UserProfilesApiResponse } from "@/lib/Types";

export const sessionContext: SessionContext = {
  ApiUrl: "/account/dashboard/profile-image/",
  csrfCookieName: "csrftoken",
  djangoSessionCookieName: "sessionid",
  cookieDomain: "localhost",
  debugMode: false,
  smarterClient: "@smarter/dashboard-user-menu",
  smarterClientVersion: "0.0.0",
  smarterRequestId: "storybook-request-id",
};

/** The Django dev server's static files, which Storybook's stylesheets also come from. */
const STATIC_URL = "http://localhost:9357/static/";

/** A student who is enrolled in two courses, so has two profiles. */
export const appContext: AppContext = {
  sessionContext,
  isAuthenticated: true,
  user: {
    username: "ada",
    email: "ada@example.edu",
    firstName: "Ada",
    lastName: "Lovelace",
    isSuperuser: false,
    isStaff: false,
  },
  profileImageUrl: `${STATIC_URL}images/avatars/default-profile.svg`,
  userProfileCount: 2,
  accountNumber: "1234-5678-9012",
  accountName: "Introduction to Prompt Engineering",
  languages: [
    { code: "en", name: "English" },
    { code: "es", name: "Español" },
    { code: "fr", name: "Français" },
    { code: "pt-br", name: "Português Brasileiro" },
  ],
  currentLanguage: "en",
  urls: {
    setLanguage: "/i18n/setlang/",
    next: "/dashboard/",
    profileImageApi: "/account/dashboard/profile-image/",
    userProfilesApi: "/account/dashboard/user-profiles/",
    userProfileSelectApi: "/account/dashboard/user-profiles/select/",
    login: "/login/",
    logout: "/logout/",
  },
};

/** A user with one profile, who has no Change Profile item. */
export const singleProfileAppContext: AppContext = { ...appContext, userProfileCount: 1 };

/** An anonymous request: Sign In, and the languages. */
export const anonymousAppContext: AppContext = {
  ...appContext,
  isAuthenticated: false,
  user: { username: "", email: "", firstName: "", lastName: "", isSuperuser: false, isStaff: false },
  userProfileCount: 0,
  accountNumber: "",
  accountName: "",
};

export const userProfiles: UserProfilesApiResponse = {
  userProfiles: [
    {
      id: 12,
      accountNumber: "1234-5678-9012",
      accountName: "Introduction to Prompt Engineering",
      createdAt: "2026-09-01T14:03:00Z",
      isCurrent: true,
    },
    {
      id: 7,
      accountNumber: "9876-5432-1098",
      accountName: "Building AI Agents",
      createdAt: "2026-01-15T09:30:00Z",
      isCurrent: false,
    },
  ],
};

/** What the select api returns once the second profile is chosen. */
export const switchedUserProfiles: UserProfilesApiResponse = {
  userProfiles: userProfiles.userProfiles.map((userProfile) => ({ ...userProfile, isCurrent: userProfile.id === 7 })),
};
