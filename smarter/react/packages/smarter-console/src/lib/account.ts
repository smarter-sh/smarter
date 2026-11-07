/**
 * The console's calls to the account api, /api/web/account/: signing in and out, signing up and activating an
 * account, and resetting a password. See smarter.apps.account.api.web.views.
 */
import { gettext } from "@smarter/common";

import type {
  AccountErrors,
  AccountMessage,
  ConsoleCookies,
  ConsoleSession,
  NewPasswordRequest,
  SignInRequest,
  SignUpRequest,
} from "@/contract.gen";
import { ApiError, getJson, postJson } from "@/lib/api";

/** The console's account api. See smarter.apps.account.api.web.urls. */
export const ACCOUNT_API = "/api/web/account";

export const accountUrls = {
  signIn: `${ACCOUNT_API}/login/`,
  signOut: `${ACCOUNT_API}/logout/`,
  signUp: `${ACCOUNT_API}/register/`,
  activate: (uidb64: string, token: string) =>
    `${ACCOUNT_API}/activate/${encodeURIComponent(uidb64)}/${encodeURIComponent(token)}/`,
  activationResend: `${ACCOUNT_API}/activation-resend/`,
  passwordResetRequest: `${ACCOUNT_API}/password-reset-request/`,
  passwordReset: (uidb64: string, token: string) =>
    `${ACCOUNT_API}/password-reset/${encodeURIComponent(uidb64)}/${encodeURIComponent(token)}/`,
};

export function signIn(cookies: ConsoleCookies, body: SignInRequest): Promise<ConsoleSession> {
  return postJson<ConsoleSession>(accountUrls.signIn, body, cookies);
}

export function signOut(cookies: ConsoleCookies): Promise<ConsoleSession> {
  return postJson<ConsoleSession>(accountUrls.signOut, {}, cookies);
}

/** Create an inactive user, whom the backend emails a link to activate their account. */
export function signUp(cookies: ConsoleCookies, body: SignUpRequest): Promise<AccountMessage> {
  return postJson<AccountMessage>(accountUrls.signUp, body, cookies);
}

/** Activate the account of an emailed link, and sign its user in. */
export function activate(cookies: ConsoleCookies, uidb64: string, token: string): Promise<ConsoleSession> {
  return postJson<ConsoleSession>(accountUrls.activate(uidb64, token), {}, cookies);
}

/** Email a new activation link, if the address has an account that is waiting to be activated. */
export function resendActivation(cookies: ConsoleCookies, email: string): Promise<AccountMessage> {
  return postJson<AccountMessage>(accountUrls.activationResend, { email }, cookies);
}

export function requestPasswordReset(cookies: ConsoleCookies, email: string): Promise<AccountMessage> {
  return postJson<AccountMessage>(accountUrls.passwordResetRequest, { email }, cookies);
}

export function checkPasswordResetLink(uidb64: string, token: string): Promise<AccountMessage> {
  return getJson<AccountMessage>(accountUrls.passwordReset(uidb64, token));
}

export function resetPassword(
  cookies: ConsoleCookies,
  uidb64: string,
  token: string,
  body: NewPasswordRequest,
): Promise<AccountMessage> {
  return postJson<AccountMessage>(accountUrls.passwordReset(uidb64, token), body, cookies);
}

/** Whether a response body is the account api's AccountErrors. */
function isAccountErrors(body: unknown): body is AccountErrors {
  if (!body || typeof body !== "object") return false;
  const candidate = body as Partial<AccountErrors>;
  return typeof candidate.detail === "string" && typeof candidate.fieldErrors === "object";
}

/**
 * Whether signing in failed because the account isn't activated yet: the backend's 403 with its own errors,
 * which it sends only for the right password. A 403 without them is Django's CSRF refusal.
 */
export function isInactiveAccount(error: unknown): boolean {
  return error instanceof ApiError && error.status === 403 && isAccountErrors(error.body);
}

/**
 * The errors to show for a failed account call: the api's own, or a message for a failure that it didn't
 * explain, such as an unreachable server.
 */
export function accountErrors(error: unknown): AccountErrors {
  if (error instanceof ApiError && isAccountErrors(error.body)) {
    return error.body;
  }
  if (error instanceof ApiError && error.status === 403) {
    return { detail: gettext("Your session has expired. Reload the page, and try again."), fieldErrors: {} };
  }
  return { detail: gettext("An unknown error occurred. Please try again later."), fieldErrors: {} };
}
