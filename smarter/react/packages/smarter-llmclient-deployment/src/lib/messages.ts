/**
 * The notices of the workbench's api key actions, in the user's language: what an action did, or why
 * it failed. The api says why with a code, whose English message is meant for logs and developers.
 */
import { gettext, interpolate } from "@smarter/common";

import { ApiError } from "./api";

/** What the user asked for: which action, and the api key's name, if it has one. */
export type ApiKeyAction =
  { action: "create"; name: string; attached: boolean } | { action: "attach"; name: string } | { action: "detach" };

/** What an action that succeeded did. */
export function successMessage(done: ApiKeyAction): string {
  switch (done.action) {
    case "create":
      return done.attached
        ? interpolate(
            gettext("%(name)s is created, and attached. Every request to the LLMClient's url now needs it."),
            { name: done.name },
          )
        : interpolate(gettext("%(name)s is created."), { name: done.name });
    case "attach":
      return interpolate(gettext("%(name)s is attached. Every request to the LLMClient's url now needs it."), {
        name: done.name,
      });
    case "detach":
      return gettext("The api key is detached. The LLMClient's url is public again.");
  }
}

/**
 * Why an action failed.
 *
 * @param error - What the action threw: an ApiError, or a network error.
 * @param name - The api key's name, in the request, if it had one.
 */
export function errorMessage(error: unknown, name = ""): string {
  if (!(error instanceof ApiError)) {
    return interpolate(gettext("The request failed: %(error)s"), {
      error: error instanceof Error ? error.message : String(error),
    });
  }
  switch (error.code) {
    case "not_owner":
      return gettext("Only the LLMClient's owner, or an account admin, can change its api key.");
    case "not_admin":
      return gettext("Only an account admin can create api keys.");
    case "not_account_admin":
      return gettext("Only an admin of the LLMClient's account can create its api keys.");
    case "invalid_name":
      return gettext("Give the api key a name, in snake_case, e.g. my_site_chat.");
    case "duplicate_name":
      return interpolate(gettext("You already have an api key named %(name)s."), { name });
    case "api_key_not_found":
      return gettext("That api key was not found.");
    case "not_found":
      return gettext("This LLMClient was not found. Reload the page.");
    case "invalid_request":
      return gettext("The request is not valid. Reload the page, and try again.");
    default:
      return interpolate(gettext("The request failed: %(status)s %(statusText)s"), {
        status: error.status,
        statusText: error.statusText,
      }).trim();
  }
}
