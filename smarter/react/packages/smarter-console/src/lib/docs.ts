/**
 * The docs pages: the example manifests and the JSON Schemas of the SAM kinds, and the api's OpenAPI document. They
 * are public, as the api that they read is: the kinds come from the session (samKinds), a kind's example manifest and
 * JSON Schema from the cli api, and the OpenAPI document from /api/v1/openapi.json. See smarter.apps.docs.
 */
import { ApiError, postJson } from "@/lib/api";
import type { ConsoleCookies } from "@/contract.gen";

/** The docs' pages. The backend serves the console at each, with a trailing slash. */
export const DOCS_PATH = "/docs";
export const MANIFESTS_PATH = "/docs/manifests";
export const JSON_SCHEMAS_PATH = "/docs/json-schemas";
export const OPENAPI_PATH = "/docs/openapi";

/** The api's OpenAPI document. See smarter.apps.api.v1.contract.views. */
export const OPENAPI_JSON_URL = "/api/v1/openapi.json";

/** Scalar's build, relative to the console's built scripts, which Vite writes into assets/. */
const SCALAR_FROM_ASSETS = "../scalar/standalone.js";

/**
 * Scalar's vendored build, which renders the OpenAPI document: the console ships it (public/scalar/), and the
 * OpenAPI page loads it, so that no other page downloads its 4 MB. A build finds it beside its own scripts, which
 * may be on the CDN (SMARTER_STATIC_FILES_ON_CDN); Vite's dev server serves it at its base.
 */
export const SCALAR_SCRIPT_URL = import.meta.env.DEV
  ? `${import.meta.env.BASE_URL}scalar/standalone.js`
  : new URL(SCALAR_FROM_ASSETS, import.meta.url).href;

/** About the api contract, in the project's documentation. */
export const API_CONTRACT_DOCS_URL = "https://docs.smarter.sh/smarter-framework/smarter-api/api-contract.html";

/** The project's tools for manifests, which the docs pages link to. */
export const DOCS_TOOLS = {
  cli: "https://smarter.sh/cli/",
  vscode: "https://marketplace.visualstudio.com/items?itemName=Querium.smarter-manifest",
  npm: "https://www.npmjs.com/package/@smarter.sh/ui-chat",
  pypi: "https://pypi.org/project/smarter-api/",
  github: "https://github.com/smarter-sh/",
};

/** The route of a kind's example manifest, e.g. /docs/manifest/llmclient. Its url is lower case, as Django's was. */
export function manifestPath(kind: string): string {
  return `/docs/manifest/${kind.toLowerCase()}`;
}

/** The route of a kind's JSON Schema, e.g. /docs/json-schema/llmclient. */
export function jsonSchemaPath(kind: string): string {
  return `/docs/json-schema/${kind.toLowerCase()}`;
}

/**
 * The kind that a route names, in its own case.
 *
 * @param slug - The route's kind, e.g. llmclient.
 * @param kinds - The session's SAM kinds.
 * @returns The kind, e.g. LLMClient, or null when it isn't one.
 */
export function kindOf(slug: string, kinds: string[]): string | null {
  const lower = slug.toLowerCase();
  return kinds.find((kind) => kind.toLowerCase() === lower) ?? null;
}

/** What the docs pages show of a kind: its example manifest, or its manifest's JSON Schema. */
export type KindDocument = "manifest" | "json-schema";

/** The cli api's url of a kind's document, e.g. /api/v1/cli/example-manifest/llmclient/. */
export function kindDocumentUrl(document: KindDocument, kind: string): string {
  const route = document === "manifest" ? "example-manifest" : "json-schema";
  return `/api/v1/cli/${route}/${kind.toLowerCase()}/`;
}

/** The cli api's journaled answer: its data. */
interface Journaled {
  data?: unknown;
}

/**
 * Load a kind's example manifest or JSON Schema from the cli api, which is public.
 *
 * @param document - Which document.
 * @param kind - The kind.
 * @param cookies - The session's cookies, for the CSRF token of the POST.
 * @returns The document, as an object.
 * @throws ApiError when the api answers with an error, or with no data.
 */
export async function loadKindDocument(
  document: KindDocument,
  kind: string,
  cookies: ConsoleCookies,
): Promise<Record<string, unknown>> {
  const url = kindDocumentUrl(document, kind);
  const body = await postJson<Journaled>(url, {}, cookies);
  const data = body.data;
  if (!data || typeof data !== "object") {
    throw new ApiError(url, 200, body);
  }
  return data as Record<string, unknown>;
}
