/**
 * Scalar, which renders the api's OpenAPI document on the OpenAPI page: the console ships its standalone build
 * (public/scalar/), and the page loads it on its first visit.
 *
 * Scalar is configured to call none of its own services: no telemetry, no fonts.scalar.com, no proxy.scalar.com,
 * and no Scalar-hosted agent or developer tools (share, deploy), so that "Test Request" goes straight to this
 * platform, and a platform without internet access still renders the page. See public/scalar/README.md.
 */
import { OPENAPI_JSON_URL, SCALAR_SCRIPT_URL } from "@/lib/docs";

/** What the page uses of Scalar's standalone build, which defines window.Scalar. */
export interface ScalarApp {
  destroy?: () => void;
}

export interface ScalarGlobal {
  createApiReference: (element: HTMLElement, configuration: Record<string, unknown>) => ScalarApp | undefined;
}

declare global {
  interface Window {
    Scalar?: ScalarGlobal;
  }
}

/** The configuration of the reference: the document, and none of Scalar's services. */
export const SCALAR_CONFIGURATION = {
  url: OPENAPI_JSON_URL,
  proxyUrl: "",
  telemetry: false,
  withDefaultFonts: false,
  showDeveloperTools: "never",
  agent: { disabled: true },
  persistAuth: true,
  authentication: {
    preferredSecurityScheme: "ApiKeyAuth",
    securitySchemes: { ApiKeyAuth: { value: "Token " } },
  },
};

let scalarLoading: Promise<ScalarGlobal> | null = null;

/**
 * Scalar, which the page's first visit loads, once.
 *
 * @returns window.Scalar, once its script has run.
 */
export function loadScalar(): Promise<ScalarGlobal> {
  if (window.Scalar) return Promise.resolve(window.Scalar);
  if (scalarLoading) return scalarLoading;
  scalarLoading = new Promise<ScalarGlobal>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = SCALAR_SCRIPT_URL;
    script.async = true;
    script.addEventListener("load", () => {
      if (window.Scalar) {
        resolve(window.Scalar);
      } else {
        reject(new Error(`${SCALAR_SCRIPT_URL} didn't define window.Scalar`));
      }
    });
    script.addEventListener("error", () => reject(new Error(`${SCALAR_SCRIPT_URL} failed to load`)));
    document.head.appendChild(script);
  }).finally(() => {
    // once loaded, window.Scalar answers later calls; after a failure, a later visit tries again.
    scalarLoading = null;
  });
  return scalarLoading;
}
