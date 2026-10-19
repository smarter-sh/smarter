/**
 * Example data for the workbench's stories and tests: its configuration, the LLMClient's chat configuration, as the
 * config api returns it (a trimmed copy of a real response, for the stackademy_sql LLMClient, as Smarter Chat's own
 * fixtures have it), and the LLMClient's manifest. The server logs, the architecture and the deployment page are
 * @smarter/serverlogs', @smarter/llmclient-architecture's and @smarter/llmclient-deployment's own fixtures.
 */
import { normalizeConfig, type ChatConfig, type Contract } from "@smarter.sh/ui-chat";
import type { SessionContext } from "@smarter/common";

import type { WorkbenchConfig } from "@/lib/types";

const HASHED_ID = "rMTAwMDAwMQx";
export const API_URL = `http://localhost:9357/workbench/llm-clients/${HASHED_ID}/`;
export const CONFIG_URL = `${API_URL}config/`;
export const PROMPT_URL = `http://localhost:9357/api/v1/llm-clients/${HASHED_ID}/prompt/`;
export const LOG_STREAM_URL = "http://localhost:9357/dashboard/logs/api/stream/";
export const MANIFEST_URL = `/workbench/llm-clients/${HASHED_ID}/manifest/editor/`;
export const ARCHITECTURE_URL = `/workbench/llm-clients/${HASHED_ID}/architecture/`;
export const DEPLOYMENT_URL = `/workbench/llm-clients/${HASHED_ID}/deployment/`;
export const LLMCLIENT_LIST_URL = "/workbench/";
export const SESSION_KEY = "e019a5c1cb2c1cb87992d2d03bccaf44c9d98406b46de5516a4fa03650038ac8";

export const session: SessionContext = {
  ApiUrl: "/api/v1/cli/apply/",
  csrfCookieName: "csrftoken",
  djangoSessionCookieName: "sessionid",
  cookieDomain: "localhost",
  debugMode: false,
  smarterClient: "@smarter/workbench",
  smarterClientVersion: "0.1.0",
  smarterRequestId: "test-request-id",
  smarterCapabilities: ["custom"],
};

/** The workbench's configuration, as main.tsx reads it from the root element, with every tab. */
export const workbench: WorkbenchConfig = {
  apiUrl: API_URL,
  toggleMetadata: true,
  csrfCookieName: "csrftoken",
  sessionCookieName: "session_key",
  cookieDomain: "localhost",
  debugMode: false,
  smarterRequestId: "test-request-id",
  logStreamUrl: LOG_STREAM_URL,
  manifestUrl: MANIFEST_URL,
  architectureUrl: ARCHITECTURE_URL,
  deploymentUrl: DEPLOYMENT_URL,
  llmclientListUrl: LLMCLIENT_LIST_URL,
  applyApiUrl: "/api/v1/cli/apply/",
  validateApiUrl: "/api/v1/cli/validate/",
  deleteApiUrl: "/api/v1/cli/delete/__kind__/",
  kindPlaceholder: "__kind__",
  session,
};

/** The workbench's configuration without the optional tabs: no server logs, manifest, architecture or deployment. */
export const plainWorkbench: WorkbenchConfig = {
  ...workbench,
  logStreamUrl: null,
  manifestUrl: null,
  architectureUrl: null,
  deploymentUrl: null,
};

export function makeConfig(overrides: Partial<Contract.PromptChatApiConfig> = {}): ChatConfig {
  const chatConfig = normalizeConfig({
    contract: 2,
    session_key: SESSION_KEY,
    sandbox_mode: true,
    debug_mode: false,
    llmclient: {
      id: 1,
      url_llmclient: PROMPT_URL,
      user_profile: {
        user: { username: "admin", email: "admin@smarter.sh" },
        account: { accountNumber: "3141-5926-5359" },
      },
      default_system_role: "You are a helpful assistant. DO NOT GUESS.",
      name: "stackademy_sql",
      description: "Stackademy University course catalogue inquiries using the Stackademy SQL plugin.",
      version: "1.0.0",
      deployed: false,
      provider: "openai",
      default_model: "gpt-4o-mini",
      default_temperature: 1.0,
      default_max_tokens: 1024,
      app_name: "Stackademy",
      app_assistant: "Stanley",
      app_welcome_message: "Welcome to Stackademy! How can I help you today?",
      app_example_prompts: ["Do you offer any courses on AI?"],
      app_placeholder: "Ask me anything about Stackademy courses...",
      app_info_url: "https://stackademy.edu/online-courses",
      app_file_attachment: false,
      total_tools: 1,
    },
    history: { chat_history: [], prompt_tool_call_history: [] },
    meta_data: { ready: true, is_deployed: false, is_chatbot_sandbox_url: true, url: CONFIG_URL },
    plugins: { meta_data: { total_plugins: 0, plugins_returned: 0 }, plugins: [] },
    ...overrides,
  });
  if (!chatConfig) throw new Error("The example configuration is not a valid configuration.");
  return chatConfig;
}

export const config = makeConfig();

/** A chat session in progress, with a tool call. */
export const configWithHistory = makeConfig({
  history: {
    chat_history: [],
    prompt_tool_call_history: [
      {
        id: 1,
        created_at: "2026-01-01T12:00:01Z",
        updated_at: "2026-01-01T12:00:01Z",
        prompt: 7,
        plugin: 16,
        function_name: "stackademy_sql",
        function_args: "{}",
        request: { inquiry_type: "courses" },
        response: [{ course_code: "CS210", course_name: "Artificial Intelligence" }],
      },
    ],
  },
});

/**
 * A configuration without its diagnostic parts, as the platform returns it unless the client asks for them with
 * ?verbose=true: the session's tool calls.
 */
export function leanConfig(chatConfig: ChatConfig): ChatConfig {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { prompt_tool_call_history, ...history } = chatConfig.history;
  return makeConfig({ ...chatConfig, history });
}

/** The user's recent server logs, and a record that arrives after them: the server log viewer's own fixtures. */
export { bulkLogs, liveLog } from "@smarter/serverlogs/mocks";

/** The LLMClient's manifest, as the Manifest tab fetches it. */
export const MANIFEST_YAML = `apiVersion: smarter.sh/v1
kind: LLMClient
metadata:
  name: stackademy_sql
  description: Stackademy University course catalogue inquiries.
  version: 1.0.0
spec:
  config:
    prompt:
      provider: openai
      defaultModel: gpt-4o-mini
`;
