/** Example data for this package's stories and tests. See smarter.apps.api.v1.cli.views.apply. */
import type { SessionContext } from "@smarter/common";

export const API_URL = "/api/v1/cli/apply/";

export const sessionContext: SessionContext = {
  ApiUrl: API_URL,
  csrfCookieName: "csrftoken",
  djangoSessionCookieName: "sessionid",
  cookieDomain: "localhost",
  debugMode: false,
  smarterClient: "@smarter/manifest-dropzone",
  smarterClientVersion: "0.0.0",
  smarterRequestId: "storybook-request-id",
};

export const SECRET_MANIFEST = `apiVersion: smarter.sh/v1
kind: Secret
metadata:
  name: example_secret
  description: An example secret.
  version: 1.0.0
spec:
  config:
    value: not-a-real-secret
`;

/** What the apply api returns for SECRET_MANIFEST. */
export const applyResult = {
  message: "Secret example_secret applied successfully",
  data: { data: { metadata: { name: "example_secret", version: "1.0.0", description: "An example secret." } } },
};
