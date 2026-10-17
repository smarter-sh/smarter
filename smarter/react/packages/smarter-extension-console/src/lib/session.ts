/**
 * Reads the app's context from the attributes of its root element, which Django renders: see
 * smarter.apps.llmtool.extension.views and templates/react/extension-{list,detail}.html.
 */
import type { SessionContext } from "@smarter/common";

import { projectName, projectVersion } from "@/lib/const";
import type { ConsoleContext } from "@/lib/types";

/** The root element of the Extensions list page. */
export const LIST_ROOT_ID = "smarter-extension-list-root";
/** The root element of an extension's page. */
export const DETAIL_ROOT_ID = "smarter-extension-detail-root";

/**
 * Return the app's context, from its root element's attributes.
 *
 * @param rootEl - The root element.
 * @returns The context; it has a slug on an extension's page.
 * @throws If a required attribute is missing.
 */
export function readContext(rootEl: HTMLElement): ConsoleContext {
  const attribute = (name: string, required = true): string => {
    const value = rootEl.getAttribute(name) || "";
    if (required && !value) throw new Error(`The Extensions app's root element has no ${name} attribute.`);
    return value;
  };
  const apiUrl = attribute("smarter-extension-api-url");
  const session: SessionContext = {
    ApiUrl: apiUrl,
    csrfCookieName: attribute("django-csrf-cookie-name"),
    djangoSessionCookieName: attribute("django-session-cookie-name"),
    cookieDomain: attribute("django-cookie-domain", false) || window.location.hostname,
    debugMode: attribute("react-debug-mode", false).toLowerCase() === "true",
    smarterClient: projectName,
    smarterClientVersion: projectVersion,
    smarterRequestId: attribute("smarter-request-id"),
  };
  const slug = rootEl.id === DETAIL_ROOT_ID ? attribute("smarter-extension-slug") : undefined;
  const canEdit = attribute("smarter-extension-can-edit", false).toLowerCase() === "true";
  return { session, apiUrl, listUrl: attribute("smarter-extension-list-url"), slug, canEdit };
}
