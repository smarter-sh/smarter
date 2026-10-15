/**
 * The client of the Extensions api: smarter.apps.llmtool.extension.views.
 *
 * Every endpoint is a POST, relative to the api's root (ConsoleContext.apiUrl). A failure is an
 * ApiError, whose message is the api's {"error": "..."}, meant for the person who tried the action.
 */
import { fetchDjangoUrl, getCookie } from "@smarter/common";

import type {
  AccountsResponse,
  ActionResponse,
  AvailabilityRequest,
  ConfigureRequest,
  ConsoleContext,
  ExtensionDetailResponse,
  ExtensionListResponse,
  RegistryResponse,
} from "@/lib/types";

/** A failed request: the api's error message, and the HTTP status. */
export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** The message of an error that an api call threw. */
export function errorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/** The error message of a failed response. */
function errorMessage(data: unknown, response: Response): string {
  if (data && typeof data === "object" && "error" in data && typeof data.error === "string") return data.error;
  return `The request failed: ${response.status} ${response.statusText}`.trim();
}

/** Parse a response, and throw an ApiError if it failed. */
async function parse<T>(response: Response): Promise<T> {
  let data: unknown;
  try {
    data = await response.json();
  } catch {
    data = null;
  }
  if (!response.ok) throw new ApiError(errorMessage(data, response), response.status);
  return data as T;
}

/** POST a JSON body to an endpoint, relative to the api's root, and return its JSON. */
export async function post<T>(context: ConsoleContext, path: string, body: object = {}): Promise<T> {
  return parse<T>(await fetchDjangoUrl(context.session, `${context.apiUrl}${path}`, JSON.stringify(body)));
}

/** The url of an endpoint of one extension. */
const of = (slug: string, action = "") => `extensions/${encodeURIComponent(slug)}/${action ? `${action}/` : ""}`;

export const listExtensions = (context: ConsoleContext) => post<ExtensionListResponse>(context, "list/");
export const getRegistry = (context: ConsoleContext, refresh = false) =>
  post<RegistryResponse>(context, "registry/", { refresh });
export const checkUpdates = (context: ConsoleContext) => post<ActionResponse>(context, "check-updates/");
export const install = (context: ConsoleContext, slug: string, version?: string | null) =>
  post<ActionResponse>(context, "install/", { slug, version: version ?? null });
export const getAccounts = (context: ConsoleContext) => post<AccountsResponse>(context, "accounts/");
export const getExtension = (context: ConsoleContext, slug: string) => post<ExtensionDetailResponse>(context, of(slug));
export const enable = (context: ConsoleContext, slug: string) => post<ActionResponse>(context, of(slug, "enable"));
export const disable = (context: ConsoleContext, slug: string) => post<ActionResponse>(context, of(slug, "disable"));
export const update = (context: ConsoleContext, slug: string) => post<ActionResponse>(context, of(slug, "update"));
export const rollback = (context: ConsoleContext, slug: string, versionId: number) =>
  post<ActionResponse>(context, of(slug, "rollback"), { versionId });
export const configure = (context: ConsoleContext, slug: string, request: ConfigureRequest) =>
  post<ActionResponse>(context, of(slug, "configure"), request);
export const setAvailability = (context: ConsoleContext, slug: string, request: AvailabilityRequest) =>
  post<ActionResponse>(context, of(slug, "availability"), request);
export const uninstall = (context: ConsoleContext, slug: string) =>
  post<ActionResponse>(context, of(slug, "uninstall"));

/**
 * Upload an extension's archive, and install it.
 *
 * It is a multipart request, with the headers that fetchDjangoUrl sends, but without its JSON
 * content type, which the browser sets, with the multipart boundary.
 */
export async function uploadArchive(context: ConsoleContext, file: File): Promise<ActionResponse> {
  const { session } = context;
  const form = new FormData();
  form.append("archive", file);
  const response = await fetch(`${context.apiUrl}upload/`, {
    method: "POST",
    credentials: "include",
    headers: {
      Accept: "application/json",
      "X-CSRFToken": getCookie({ name: session.csrfCookieName, domain: session.cookieDomain }) || "",
      "X-Smarter-Client": session.smarterClient,
      "X-Smarter-ClientVersion": session.smarterClientVersion,
      "X-Smarter-ClientType": "react",
      "X-Smarter-RequestId": session.smarterRequestId,
    },
    body: form,
  });
  return parse<ActionResponse>(response);
}
