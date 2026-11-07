/**
 * The user menu's context, from the console's session. The user menu (@smarter/dashboard-user-menu) is also
 * mounted on the pages that the backend still renders, from the attributes of its template; in the console it
 * takes the same values from the session.
 */
import type { SessionContext } from "@smarter/common";
import type { AppContext } from "@smarter/dashboard-user-menu";

import type { ConsoleSession } from "@/contract.gen";
import { ACCOUNT_API, accountUrls } from "@/lib/account";
import { LOGIN_PATH, projectName, projectVersion } from "@/lib/const";

/** The backend's urls that the user menu calls: Django's set_language view, and the console's account api. */
export const userMenuUrls = {
  setLanguage: "/i18n/setlang/",
  profileImageApi: `${ACCOUNT_API}/profile-image/`,
  userProfilesApi: `${ACCOUNT_API}/user-profiles/`,
  userProfileSelectApi: `${ACCOUNT_API}/user-profiles/select/`,
};

/** A new id for the user menu's requests, which the backend logs: 32 hex digits. */
function requestId(): string {
  return crypto.randomUUID().replaceAll("-", "");
}

/**
 * The user menu's context, for a signed-in session.
 *
 * @param session - The console's session.
 * @param path - The page's path, to return to after choosing a language.
 * @returns The context.
 */
export function userMenuContext(session: ConsoleSession, path: string): AppContext {
  const { cookies, user, account, language, flags } = session;
  const sessionContext: SessionContext = {
    ApiUrl: userMenuUrls.profileImageApi,
    csrfCookieName: cookies.csrfCookieName,
    djangoSessionCookieName: cookies.sessionCookieName,
    cookieDomain: cookies.cookieDomain || window.location.hostname,
    debugMode: flags.reactDebugMode,
    smarterClient: projectName,
    smarterClientVersion: projectVersion,
    smarterRequestId: requestId(),
  };
  return {
    sessionContext,
    isAuthenticated: session.isAuthenticated,
    user: {
      username: user?.username ?? "",
      email: user?.email ?? "",
      firstName: user?.firstName ?? "",
      lastName: user?.lastName ?? "",
      isSuperuser: user?.isSuperuser ?? false,
      isStaff: user?.isStaff ?? false,
    },
    profileImageUrl: user?.profileImageUrl ?? "",
    userProfileCount: user?.userProfileCount ?? 0,
    accountNumber: account?.accountNumber ?? "",
    accountName: account?.name ?? "",
    languages: language.languages,
    currentLanguage: language.current,
    urls: {
      ...userMenuUrls,
      next: path,
      login: LOGIN_PATH,
      logout: accountUrls.signOut,
    },
  };
}
