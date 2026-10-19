/**
 * The client of the workbench's api key actions:
 * smarter.apps.prompt.views.detailviews.prompt_deployment_view.
 *
 * Each action is a POST to its url, from the page's apiKeys section. It answers with the page as it now
 * is, and, for a new api key, its secret. A failure is an ApiError, whose code says why.
 */
import { fetchDjangoUrl, type SessionContext } from "@smarter/common";

import type {
  ApiKeyActionResponse,
  AttachApiKeyRequest,
  CreateApiKeyRequest,
  DeploymentApiKeys,
  ErrorCode,
} from "./types";

/** A failed action: why, the api's English message, and the HTTP status. */
export class ApiError extends Error {
  code: ErrorCode | null;
  status: number;
  statusText: string;

  constructor(message: string, code: ErrorCode | null, status: number, statusText = "") {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.statusText = statusText;
  }
}

/** Parse a response, and throw an ApiError if it failed. */
async function parse(response: Response): Promise<ApiKeyActionResponse> {
  let data: unknown;
  try {
    data = await response.json();
  } catch {
    data = null;
  }
  if (!response.ok) {
    const error = data && typeof data === "object" ? (data as { error?: unknown; code?: unknown }) : {};
    throw new ApiError(
      typeof error.error === "string" ? error.error : response.statusText,
      typeof error.code === "string" ? (error.code as ErrorCode) : null,
      response.status,
      response.statusText,
    );
  }
  return data as ApiKeyActionResponse;
}

/** POST a JSON body to an action's url, and return the page as it now is. */
async function post(session: SessionContext, url: string, body: object = {}): Promise<ApiKeyActionResponse> {
  return parse(await fetchDjangoUrl(session, url, JSON.stringify(body)));
}

export const createApiKey = (session: SessionContext, apiKeys: DeploymentApiKeys, request: CreateApiKeyRequest) =>
  post(session, apiKeys.createUrl, request);
export const attachApiKey = (session: SessionContext, apiKeys: DeploymentApiKeys, request: AttachApiKeyRequest) =>
  post(session, apiKeys.attachUrl, request);
export const detachApiKey = (session: SessionContext, apiKeys: DeploymentApiKeys) => post(session, apiKeys.detachUrl);
