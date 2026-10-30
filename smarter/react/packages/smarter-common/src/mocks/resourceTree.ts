/**
 * Example trees for the ResourceTree widget's stories and tests, as the web console's architecture view returns
 * them (smarter.apps.prompt.views.detailviews.prompt_architecture_view). @smarter/llmclient-architecture's
 * fixtures have the same trees, in its full architectures.
 */
import type { ResourceTreeNode } from "../components/ResourceTree/types";

const OWNER = "Ada Lovelace (ada)";

/** A resource that uses nothing. */
function leaf(kind: string, icon: string, name: string, recordLocator: string, url: string | null): ResourceTreeNode {
  const detailUrl = `/dashboard/api/resource/${kind}/${recordLocator}/`;
  return { kind, icon, name, owner: OWNER, recordLocator, url, detailUrl, readable: true, children: [] };
}

const openaiKey = leaf("Secret", "lock-2", "openai_api_key", "secret-rMTAwMDAxMQx", "/secret/secrets/rMTAwMDAxMQx/");

const openai: ResourceTreeNode = {
  ...leaf("Provider", "cloud", "openai", "provider-rMTAwMDAwNwx", "/provider/providers/rMTAwMDAwNwx/"),
  children: [openaiKey],
};

/**
 * stackademy_sql: a Provider, a SQL plugin, its Connection and their Secrets, a Guardrail, an Extension, and an api
 * key.
 */
export const stackademyTree: ResourceTreeNode = {
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
    leaf(
      "SmarterAuthToken",
      "key",
      "stackademy_sql_production",
      "smarterauthtoken-1a2b3c4d",
      "/authtoken/0b8f4d3e-5c1a-4f7e-9d2b-6a1c3e5f7a9b/",
    ),
  ],
};

/** An LLMClient that uses nothing. */
export const leafTree: ResourceTreeNode = leaf(
  "LLMClient",
  "artificial-intelligence",
  "hello_world",
  "llmclient-rMTAwMDAwMgx",
  "/workbench/llm-clients/rMTAwMDAwMgx/manifest/",
);

/** An LLMClient that uses another account's Guardrail, which the user may not read. */
export const lockedTree: ResourceTreeNode = {
  ...leafTree,
  children: [
    {
      kind: "Guardrail",
      icon: "shield-tick",
      name: null,
      owner: null,
      recordLocator: "guardrail-rMTAwMDA5OQx",
      url: null,
      detailUrl: null,
      readable: false,
      children: [],
    },
  ],
};

/** The web console's list pages, as the backend reverses them. */

/** A Guardrail's tree: the Guardrail, and the Provider whose model judges, with its Secret. */
export const guardrailTree: ResourceTreeNode = {
  ...leaf("Guardrail", "shield-tick", "no_pii", "guardrail-rMTAwMDAwNQx", "/guardrail/guardrails/rMTAwMDAwNQx/"),
  children: [openai],
};

/** The LLMClients that use the Guardrail of guardrailTree, one of which the user may not read. */
export const guardrailDependents: ResourceTreeNode[] = [
  leaf(
    "LLMClient",
    "artificial-intelligence",
    "stackademy_sql",
    "llmclient-rMTAwMDAyMgx",
    "/workbench/llm-clients/rMTAwMDAyMgx/manifest/",
  ),
  {
    kind: "LLMClient",
    icon: "artificial-intelligence",
    name: null,
    owner: null,
    recordLocator: "llmclient-rMTAwMDAzMwx",
    url: null,
    detailUrl: null,
    readable: false,
    children: [],
  },
];
