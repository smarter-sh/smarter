/**
 * The types of the LLMClient deployment app: the page's contract, generated from the backend's
 * Pydantic models (see src/contract.gen.ts), and the app's own context.
 */
import type { SessionContext } from "@smarter/common";

import type { ErrorResponse, LLMClientDeploymentPage } from "../contract.gen";

export type {
  ApiKeyActionResponse,
  AttachApiKeyRequest,
  CreateApiKeyRequest,
  DeploymentApiKey,
  DeploymentApiKeys,
  DeploymentAttachedApiKey,
  DeploymentLinks,
  DeploymentLLMClient,
  DeploymentOwnership,
  DeploymentSnippets,
  ErrorResponse,
  LLMClientDeploymentPage,
  NewApiKey,
} from "../contract.gen";

/** Why an api key action failed. */
export type ErrorCode = ErrorResponse["code"];

/**
 * What the app knows about the page that hosts it.
 *
 * - page: the page's data, from its json_script.
 * - session: the Django session and CSRF cookies, and the request headers, for fetchDjangoUrl. Only
 *   the workbench's tab has one: the page at the deployed LLMClient's url has no session, and no actions.
 */
export type DeploymentContext = {
  page: LLMClientDeploymentPage;
  session: SessionContext | null;
};
