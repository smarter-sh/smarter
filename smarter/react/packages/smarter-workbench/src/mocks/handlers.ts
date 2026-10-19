/**
 * MSW request handlers for the workbench: the chat's config and prompt apis, and the Console's Manifest,
 * Architecture and Deployment tabs' data. See storybook/preview.ts and test/server.ts in the workspace.
 */
import { http, HttpResponse } from "msw";
import { stackademyTree } from "@smarter/llmclient-architecture/mocks";
import { workbenchPage } from "@smarter/llmclient-deployment/mocks";

import {
  ARCHITECTURE_URL,
  CONFIG_URL,
  DEPLOYMENT_URL,
  LOG_STREAM_URL,
  MANIFEST_URL,
  MANIFEST_YAML,
  PROMPT_URL,
  bulkLogs,
  configWithHistory,
  leanConfig,
} from "./fixtures";

/** The config api, which returns the configuration's diagnostic parts only with ?verbose=true. */
export const configHandler = http.post(CONFIG_URL, ({ request }) => {
  const verbose = new URL(request.url).searchParams.get("verbose") === "true";
  return HttpResponse.json({ data: verbose ? configWithHistory : leanConfig(configWithHistory), api: "smarter.sh/v1" });
});

/** The chat's apis, and the user's server logs. */
export const chatHandlers = [
  configHandler,
  http.post(PROMPT_URL, () =>
    HttpResponse.json({
      api: "smarter.sh/v1",
      data: { status: 200, messages: [{ role: "assistant", content: "We offer CS210 Artificial Intelligence." }] },
    }),
  ),
  http.get(LOG_STREAM_URL, () => {
    const body = `retry: 3000\n\nevent: bulk\ndata: ${JSON.stringify(bulkLogs)}\n\n`;
    return new HttpResponse(body, { headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" } });
  }),
];

/** The Manifest, Architecture and Deployment tabs' data. */
export const tabHandlers = [
  http.get(MANIFEST_URL, () => HttpResponse.json({ manifest: MANIFEST_YAML })),
  http.get(ARCHITECTURE_URL, () => HttpResponse.json(stackademyTree)),
  http.get(DEPLOYMENT_URL, () => HttpResponse.json(workbenchPage)),
];

/** The Manifest, Architecture and Deployment tabs' data fail to load. */
export const tabErrorHandlers = [
  http.get(MANIFEST_URL, () => new HttpResponse(null, { status: 500, statusText: "Internal Server Error" })),
  http.get(ARCHITECTURE_URL, () =>
    HttpResponse.json({ error: "LLMClient not found." }, { status: 404, statusText: "Not Found" }),
  ),
  http.get(DEPLOYMENT_URL, () =>
    HttpResponse.json({ error: "LLMClient not found.", code: "not_found" }, { status: 404, statusText: "Not Found" }),
  ),
];

/** Every handler of the workbench, for the whole app. */
export const workbenchHandlers = [...chatHandlers, ...tabHandlers];
