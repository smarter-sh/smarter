/**
 * Example data for this package's stories and tests: a manifest, as the web console's manifest
 * detail page gives it to the editor. See smarter.apps.docs.views.base.DocsBaseView.
 */
import type { SessionContext } from "@smarter/common";

import type { AppProps } from "@/App";

export const APPLY_API_URL = "/api/v1/cli/apply/";
export const VALIDATE_API_URL = "/api/v1/cli/validate/";
export const DELETE_API_URL = "/api/v1/cli/delete/__kind__/";

export const sessionContext: SessionContext = {
  ApiUrl: APPLY_API_URL,
  csrfCookieName: "csrftoken",
  djangoSessionCookieName: "sessionid",
  cookieDomain: "localhost",
  debugMode: false,
  smarterClient: "@smarter/manifest-editor",
  smarterClientVersion: "0.0.0",
  smarterRequestId: "storybook-request-id",
};

export const SECRET_YAML = `apiVersion: smarter.sh/v1
kind: Secret
metadata:
  name: example_secret
  description: An example secret.
  version: 1.0.0
spec:
  config:
    value: not-a-real-secret
status:
  accountNumber: 3141-5926-5359
  username: admin
`;

/** A Secret that an LLMClient depends on, so it cannot be deleted. */
export const SECRET_IN_USE_YAML = `${SECRET_YAML}  dependencies:
    - kind: LLMClient
      name: example_llmclient
`;

export const appProps: AppProps = {
  sessionContext,
  initialManifest: SECRET_YAML,
  applyApiUrl: APPLY_API_URL,
  validateApiUrl: VALIDATE_API_URL,
  deleteApiUrl: DELETE_API_URL,
  kindPlaceholder: "__kind__",
};
