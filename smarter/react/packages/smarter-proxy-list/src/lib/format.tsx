/**
 * Formatting of Proxy attributes, shared by ListView, CardView, StatusBar and Toolbar.
 */
import type { Proxy } from "@/lib/Types";

/** The absolute URL of the Proxy's passthrough endpoint, to use as the base URL of the provider's SDK. */
export function proxyUrl(proxy: Proxy): string {
  if (!proxy.url) return "";
  return new URL(proxy.url, window.location.origin).toString();
}

/** The host of the provider's API, e.g. "api.openai.com". */
export function upstreamHost(proxy: Proxy): string {
  try {
    return new URL(proxy.upstreamUrl).host;
  } catch {
    return proxy.upstreamUrl || "—";
  }
}

/** How the API key is sent, e.g. "Authorization: Bearer" or "x-api-key". */
export function formatAuth(proxy: Proxy): string {
  return proxy.authScheme ? `${proxy.authHeader}: ${proxy.authScheme}` : proxy.authHeader;
}

/** The API key's Secret, and whether it is the Proxy's own or its Provider's. */
export function formatApiKey(proxy: Proxy): string {
  if (!proxy.apiKeySecretName) return "None";
  return proxy.apiKeySecret ? proxy.apiKeySecretName : `${proxy.apiKeySecretName} (provider's)`;
}

/** The allowed paths, e.g. "4 paths", or "All paths". */
export function formatAllowedPaths(proxy: Proxy): string {
  const count = proxy.allowedPaths?.length || 0;
  if (!count) return "All paths";
  return count === 1 ? "1 path" : `${count} paths`;
}
