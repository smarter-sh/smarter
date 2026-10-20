/**
 * Types of the user menu: what main.tsx reads from the root element, and what the Django apis
 * return. See smarter.apps.dashboard.templatetags.react_dashboard_user_menu,
 * smarter.apps.account.views.dashboard.profile_image and smarter.apps.account.views.dashboard.user_profiles.
 */
import type { SessionContext } from "@smarter/common";

/** One of the languages of the console, in its own name. */
export interface Language {
  /** The language code, e.g. "pt-br", which the Language item posts to set_language. */
  code: string;
  /** The language's name in that language, e.g. "Español". */
  name: string;
}

/** Who the signed-in user is. */
export interface MenuUser {
  username: string;
  email: string;
  firstName: string;
  lastName: string;
  isSuperuser: boolean;
  isStaff: boolean;
}

/** The urls of the menu's items. */
export interface MenuUrls {
  /** Django's set_language view, which the Language item posts to. */
  setLanguage: string;
  /** The page to return to after choosing a language: this one. */
  next: string;
  /** Uploads (POST) and removes (DELETE) the user's profile image. */
  profileImageApi: string;
  /** Lists the user's profiles. */
  userProfilesApi: string;
  /** Chooses the profile that the console acts as. */
  userProfileSelectApi: string;
  login: string;
  logout: string;
}

/** The root element's attributes. See templates/react/dashboard-user-menu.html. */
export interface AppContext {
  sessionContext: SessionContext;
  /** Whether a user is signed in. An anonymous menu has only the Sign In item and the languages. */
  isAuthenticated: boolean;
  user: MenuUser;
  /** The image that represents the user. */
  profileImageUrl: string;
  /** How many profiles the user has. The Change Profile item shows with two or more. */
  userProfileCount: number;
  /** The account of the profile that the console acts as. */
  accountNumber: string;
  accountName: string;
  languages: Language[];
  /** The code of the page's language. */
  currentLanguage: string;
  urls: MenuUrls;
}

/** One of the user's profiles. See UserProfileChoice in smarter.apps.account.views.dashboard.user_profiles. */
export interface UserProfileChoice {
  id: number;
  accountNumber: string;
  accountName: string;
  /** When the profile was created, as an ISO 8601 date. */
  createdAt: string;
  /** Whether the console acts as this profile. */
  isCurrent: boolean;
}

/** The response of both user profile apis. */
export interface UserProfilesApiResponse {
  userProfiles: UserProfileChoice[];
}

/** The response of the profile image api. */
export interface ProfileImageApiResponse {
  profile_image_url?: string;
  profile_image?: string[];
  error?: string;
}
