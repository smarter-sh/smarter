/**
 * The LLMClient deployment page's contract: generated from contract/llmclient-deployment.schema.json by
 * scripts/contract-types.mjs. Do not edit; run `npm run contract:types`.
 */

/**
 * The data of an LLMClient's deployment page, and of its api key actions. Generated from smarter.apps.llmclient.views.deployment_contract; do not edit.
 */
export interface SmarterLLMClientDeploymentPageContract {
  [k: string]: unknown;
}
/**
 * The page after an api key action, and a new key's secret.
 *
 * This interface was referenced by `SmarterLLMClientDeploymentPageContract`'s JSON-Schema
 * via the `definition` "ApiKeyActionResponse".
 */
export interface ApiKeyActionResponse {
  newApiKey: NewApiKey | null;
  page: LLMClientDeploymentPage;
}
/**
 * An api key that was just created.
 *
 * Its secret is in this response only.
 *
 * This interface was referenced by `SmarterLLMClientDeploymentPageContract`'s JSON-Schema
 * via the `definition` "NewApiKey".
 */
export interface NewApiKey {
  name: string;
  secret: string;
}
/**
 * Everything that the page shows.
 *
 * This interface was referenced by `SmarterLLMClientDeploymentPageContract`'s JSON-Schema
 * via the `definition` "LLMClientDeploymentPage".
 */
export interface LLMClientDeploymentPage {
  apiKeys: DeploymentApiKeys | null;
  /**
   * Whether its url requires an api key.
   */
  authenticated: boolean;
  deployed: boolean;
  links: DeploymentLinks;
  llmclient: DeploymentLLMClient;
  /**
   * Its manifest, without its owner's username, or null if it couldn't be built.
   */
  manifestYaml: string | null;
  mode: "public" | "workbench";
  ownership: DeploymentOwnership | null;
  snippets: DeploymentSnippets;
}
/**
 * The LLMClient's api key, the account's api keys, what the user may do, and where.
 *
 * Workbench only.
 *
 * This interface was referenced by `SmarterLLMClientDeploymentPageContract`'s JSON-Schema
 * via the `definition` "DeploymentApiKeys".
 */
export interface DeploymentApiKeys {
  /**
   * Newest first.
   */
  apiKeys: DeploymentApiKey[];
  attachUrl: string;
  attached: DeploymentAttachedApiKey | null;
  /**
   * Whether the user may create an api key: staff.
   */
  canCreate: boolean;
  /**
   * Whether the user may attach and detach api keys: ownership.
   */
  canManage: boolean;
  createUrl: string;
  detachUrl: string;
}
/**
 * One of the account's api keys that the user may manage.
 *
 * This interface was referenced by `SmarterLLMClientDeploymentPageContract`'s JSON-Schema
 * via the `definition` "DeploymentApiKey".
 */
export interface DeploymentApiKey {
  description: string;
  isActive: boolean;
  /**
   * Whether it is the LLMClient's api key.
   */
  isAttached: boolean;
  keyId: string;
  lastUsedAt: string | null;
  name: string;
  /**
   * The username of the key's owner.
   */
  owner: string;
}
/**
 * The LLMClient's api key, which every request to its url needs, while it is active.
 *
 * This interface was referenced by `SmarterLLMClientDeploymentPageContract`'s JSON-Schema
 * via the `definition` "DeploymentAttachedApiKey".
 */
export interface DeploymentAttachedApiKey {
  isActive: boolean;
  name: string;
}
/**
 * The urls that the page links to, which depend on the platform's configuration.
 *
 * This interface was referenced by `SmarterLLMClientDeploymentPageContract`'s JSON-Schema
 * via the `definition` "DeploymentLinks".
 */
export interface DeploymentLinks {
  /**
   * The web console's API Keys page, absolute.
   */
  apiKeysUrl: string;
  docsUrl: string;
  logoUrl: string;
  marketingSiteUrl: string;
  productDescription: string;
  productName: string;
}
/**
 * The LLMClient, as the page describes it.
 *
 * This interface was referenced by `SmarterLLMClientDeploymentPageContract`'s JSON-Schema
 * via the `definition` "DeploymentLLMClient".
 */
export interface DeploymentLLMClient {
  /**
   * The chat's title, or the LLMClient's name if it has none.
   */
  appName: string;
  examplePrompts: string[];
  model: string | null;
  name: string;
  provider: string | null;
  /**
   * Its url, without a trailing slash: the url that it will have, if it isn't deployed.
   */
  url: string;
  version: string | null;
  /**
   * The url of its Prompt Engineer's Workbench.
   */
  workbenchUrl: string;
}
/**
 * Who owns the LLMClient, and how a user who may not change it can clone it.
 *
 * Workbench only.
 *
 * This interface was referenced by `SmarterLLMClientDeploymentPageContract`'s JSON-Schema
 * via the `definition` "DeploymentOwnership".
 */
export interface DeploymentOwnership {
  /**
   * Whether the user may change the LLMClient: ownership permission.
   */
  canEdit: boolean;
  /**
   * The url of the LLM Clients list, where it can be cloned.
   */
  llmclientListUrl: string;
  /**
   * The owner's full name and username, or the username.
   */
  owner: string;
  ownershipDocsUrl: string;
}
/**
 * The commands, manifest excerpts and code that the page shows, each in a terminal with a Copy button.
 *
 * This interface was referenced by `SmarterLLMClientDeploymentPageContract`'s JSON-Schema
 * via the `definition` "DeploymentSnippets".
 */
export interface DeploymentSnippets {
  allowedOriginsYaml: string;
  apiKeyYaml: string;
  /**
   * The curl command that POSTs to its /config/ endpoint.
   */
  configCommand: string;
  createApiKeyCommand: string;
  /**
   * The command that deploys the LLMClient.
   */
  deployCommand: string;
  /**
   * The commands that apply its manifest, and deploy it.
   */
  deployCommands: string;
  drupalInstallCommands: string;
  embedHtml: string;
  embedHtmlWithApiKey: string;
  /**
   * An abbreviated /prompt/ response, as indented JSON.
   */
  exampleResponse: string;
  npmInstallCommand: string;
  /**
   * The curl command that POSTs a prompt to its /prompt/ endpoint.
   */
  promptCommand: string;
  reactSnippet: string;
  reactSnippetWithApiKey: string;
  /**
   * The curl command that continues a chat session: its /config/ request, with the session's key.
   */
  sessionConfigCommand: string;
  /**
   * The curl command that sends a prompt in a chat session, with the session's key.
   */
  sessionPromptCommand: string;
  /**
   * The command that turns off the page at deployed LLMClients' urls, for administrators.
   */
  switchCommand: string;
}
/**
 * Attach one of the account's api keys to the LLMClient, in place of any other.
 *
 * This interface was referenced by `SmarterLLMClientDeploymentPageContract`'s JSON-Schema
 * via the `definition` "AttachApiKeyRequest".
 */
export interface AttachApiKeyRequest {
  keyId: string;
}
/**
 * Create an api key for the user, and attach it to the LLMClient if asked to.
 *
 * This interface was referenced by `SmarterLLMClientDeploymentPageContract`'s JSON-Schema
 * via the `definition` "CreateApiKeyRequest".
 */
export interface CreateApiKeyRequest {
  attach?: boolean;
  description?: string;
  /**
   * The key's name, in snake_case.
   */
  name: string;
}
/**
 * Why an api key action failed: its code, and an English message for logs and developers.
 *
 * This interface was referenced by `SmarterLLMClientDeploymentPageContract`'s JSON-Schema
 * via the `definition` "ErrorResponse".
 */
export interface ErrorResponse {
  code:
    | "not_found"
    | "invalid_request"
    | "not_owner"
    | "not_admin"
    | "not_account_admin"
    | "invalid_name"
    | "duplicate_name"
    | "api_key_not_found";
  error: string;
}
