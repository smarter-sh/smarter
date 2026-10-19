/**
 * Reads the workbench's configuration from the attributes of its root element, which Django renders: see
 * templates/react/workbench.html, and smarter.apps.prompt.views.detailviews.prompt_workbench_view.PromptWorkbenchView.
 */
import type { SessionContext } from "@smarter/common";

import { projectName, projectVersion } from "@/lib/const";
import type { WorkbenchConfig } from "@/lib/types";

/** The root element of the workbench. */
export const ROOT_ID = "smarter-workbench-root";

/**
 * Return the workbench's configuration, from its root element's attributes.
 *
 * @param rootEl - The root element.
 * @returns The configuration. The optional urls are null when their attribute is empty.
 * @throws If a required attribute is missing.
 */
export function readConfig(rootEl: HTMLElement): WorkbenchConfig {
  const attribute = (name: string, required = true): string => {
    const value = rootEl.getAttribute(name) || "";
    if (required && !value) throw new Error(`The workbench's root element has no ${name} attribute.`);
    return value;
  };
  const isTrue = (name: string) => attribute(name, false).toLowerCase() === "true";
  const csrfCookieName = attribute("smarter-csrf-cookie-name");
  const cookieDomain = attribute("smarter-cookie-domain", false) || window.location.hostname;
  const debugMode = isTrue("react-debug-mode");
  const smarterRequestId = attribute("smarter-request-id");
  const applyApiUrl = attribute("smarter-apply-api-url");
  const session: SessionContext = {
    ApiUrl: applyApiUrl,
    csrfCookieName,
    djangoSessionCookieName: attribute("smarter-django-session-cookie-name"),
    cookieDomain,
    debugMode,
    smarterClient: projectName,
    smarterClientVersion: projectVersion,
    smarterRequestId,
    smarterCapabilities: ["custom"],
  };
  return {
    apiUrl: attribute("smarter-llmclient-api-url"),
    toggleMetadata: isTrue("smarter-toggle-metadata"),
    csrfCookieName,
    sessionCookieName: attribute("smarter-session-cookie-name"),
    cookieDomain,
    debugMode,
    smarterRequestId,
    logStreamUrl: attribute("smarter-log-stream-url", false) || null,
    manifestUrl: attribute("smarter-manifest-url", false) || null,
    deploymentUrl: attribute("smarter-deployment-url", false) || null,
    llmclientListUrl: attribute("smarter-llmclient-list-url"),
    applyApiUrl,
    validateApiUrl: attribute("smarter-validate-api-url"),
    deleteApiUrl: attribute("smarter-delete-api-url"),
    kindPlaceholder: attribute("smarter-kind-placeholder"),
    session,
  };
}
