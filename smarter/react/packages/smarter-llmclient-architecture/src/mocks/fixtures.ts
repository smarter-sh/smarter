/**
 * Example architectures for the stories and tests, as LLMClientArchitectureView returns them: see
 * smarter.apps.prompt.views.detailviews.prompt_architecture_view. src/contract.test.ts checks that each matches
 * the backend's contract. The workbench's tests and stories use them too, as @smarter/llmclient-architecture/mocks.
 */
import type { LLMClientArchitecture, LLMClientArchitectureLinks, SAMDependencyTreeNode } from "../lib/types";

const OWNER = "Ada Lovelace (ada)";

/** A resource that uses nothing. */
function leaf(
  kind: string,
  icon: string,
  name: string,
  recordLocator: string,
  url: string | null,
): SAMDependencyTreeNode {
  return { kind, icon, name, owner: OWNER, recordLocator, url, readable: true, children: [] };
}

const openaiKey = leaf("Secret", "lock-2", "openai_api_key", "secret-rMTAwMDAxMQx", "/secret/secrets/rMTAwMDAxMQx/");

const openai: SAMDependencyTreeNode = {
  ...leaf("Provider", "cloud", "openai", "provider-rMTAwMDAwNwx", "/provider/providers/rMTAwMDAwNwx/"),
  children: [openaiKey],
};

/** stackademy_sql: a Provider, a SQL plugin, its Connection and their Secrets, a Guardrail, and an Extension. */
export const stackademyTree: SAMDependencyTreeNode = {
  ...leaf(
    "LLMClient",
    "artificial-intelligence",
    "stackademy_sql",
    "llmclient-rMTAwMDAyMgx",
    "/workbench/llm-clients/rMTAwMDAyMgx/manifest/",
  ),
  children: [
    leaf("Extension", "abstract-26", "weather", "extension-rMTAwMDAwMQx", "/llm-tools/extensions/weather/"),
    leaf("Guardrail", "shield-tick", "no_pii", "guardrail-rMTAwMDAwNQx", "/guardrail/guardrails/rMTAwMDAwNQx/"),
    openai,
    {
      ...leaf(
        "SqlPlugin",
        "file-sheet",
        "stackademy_sql",
        "pluginmeta-rMTAwMDAyMwx",
        "/llm-tools/plugins/rMTAwMDAyMwx/",
      ),
      children: [
        openai,
        {
          ...leaf(
            "SqlConnection",
            "data",
            "smarter_test_db",
            "sqlconnection-rMTAwMDAwMQx",
            "/connection/connections/sql-connection/rMTAwMDAwMQx/",
          ),
          children: [
            leaf("Secret", "lock-2", "smarter_test_user", "secret-rMTAwMDAxNQx", "/secret/secrets/rMTAwMDAxNQx/"),
          ],
        },
      ],
    },
  ],
};

/** An LLMClient that uses nothing. */
export const leafTree: SAMDependencyTreeNode = leaf(
  "LLMClient",
  "artificial-intelligence",
  "hello_world",
  "llmclient-rMTAwMDAwMgx",
  "/workbench/llm-clients/rMTAwMDAwMgx/manifest/",
);

/** An LLMClient that uses another account's Guardrail, which the user may not read. */
export const lockedTree: SAMDependencyTreeNode = {
  ...leafTree,
  children: [
    {
      kind: "Guardrail",
      icon: "shield-tick",
      name: null,
      owner: null,
      recordLocator: "guardrail-rMTAwMDA5OQx",
      url: null,
      readable: false,
      children: [],
    },
  ],
};

/** The web console's list pages, as the backend reverses them. */
export const consoleLinks: LLMClientArchitectureLinks = {
  guardrailsUrl: "/guardrail/",
  pluginsUrl: "/llm-tools/",
  extensionsUrl: "/extensions/",
  mcpClientsUrl: "/mcpclient/",
};

/** stackademy_sql, styled: it has everything, so the tab suggests nothing. */
export const stackademyArchitecture: LLMClientArchitecture = {
  tree: stackademyTree,
  styled: true,
  links: consoleLinks,
};

/** hello_world, which uses nothing, and isn't styled: the tab suggests a Guardrail, tools and styles. */
export const leafArchitecture: LLMClientArchitecture = { tree: leafTree, styled: false, links: consoleLinks };

/** An LLMClient with another account's Guardrail, unstyled: the tab suggests tools and styles. */
export const lockedArchitecture: LLMClientArchitecture = { tree: lockedTree, styled: false, links: consoleLinks };
