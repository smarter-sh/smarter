/**
 * The api's responses that the stories and tests use, shaped by the contract: src/contract.test.ts
 * checks each of them against contract/extension-console.schema.json.
 */
import type { SessionContext } from "@smarter/common";

import type {
  ActionResponse,
  ConsoleContext,
  ExtensionDetail,
  ExtensionListResponse,
  ExtensionSummary,
  RegistryExtension,
  RegistryResponse,
} from "@/lib/types";

export const API_URL = "/extensions/react-integration/api/";
export const LIST_URL = "/extensions/";

export const session: SessionContext = {
  ApiUrl: API_URL,
  csrfCookieName: "csrftoken",
  djangoSessionCookieName: "sessionid",
  cookieDomain: "localhost",
  debugMode: false,
  smarterClient: "@smarter/extension-console",
  smarterClientVersion: "0.1.0",
  smarterRequestId: "test-request-id",
};

export const listContext: ConsoleContext = { session, apiUrl: API_URL, listUrl: LIST_URL };
export const detailContext: ConsoleContext = { ...listContext, slug: "weather" };

export function makeSummary(overrides: Partial<ExtensionSummary> = {}): ExtensionSummary {
  return {
    id: 1,
    slug: "weather",
    displayName: "Weather",
    description: "Current weather and a 24-hour forecast for any location.",
    publisher: "smarter-sh",
    source: "registry",
    trustBadge: "official",
    trustBadgeLabel: "Official Smarter Extension",
    enabled: true,
    installedVersion: "0.1.0",
    latestVersion: "0.2.0",
    updateAvailable: true,
    latestCheckedAt: "2026-10-15T12:00:00Z",
    error: "",
    detailUrl: "/extensions/weather/",
    ...overrides,
  };
}

export const installed: ExtensionSummary[] = [
  makeSummary(),
  makeSummary({
    id: 2,
    slug: "calculator",
    displayName: "Calculator",
    description: "Evaluates math expressions exactly.",
    latestVersion: "0.1.0",
    updateAvailable: false,
    detailUrl: "/extensions/calculator/",
  }),
  makeSummary({
    id: 3,
    slug: "acme-crm",
    displayName: "Acme CRM",
    description: "Looks up customers in Acme CRM.",
    publisher: "Acme Corp",
    source: "upload",
    trustBadge: "unverified",
    trustBadgeLabel: "Unverified",
    enabled: false,
    installedVersion: "1.0.0",
    latestVersion: null,
    updateAvailable: false,
    latestCheckedAt: null,
    error: "acme-crm 1.0.0 was installed, but: post_install failed",
    detailUrl: "/extensions/acme-crm/",
  }),
];

export const listResponse: ExtensionListResponse = { objects: installed, registryEnabled: true, updatesAvailable: 1 };

export function makeRegistryExtension(overrides: Partial<RegistryExtension> = {}): RegistryExtension {
  return {
    slug: "weather",
    displayName: "Weather",
    description: "Current weather and a 24-hour forecast for any location.",
    publisher: "The Smarter Project",
    publisherUrl: "https://smarter.sh",
    trustBadge: "official",
    trustBadgeLabel: "Official Smarter Extension",
    homepage: "https://github.com/smarter-sh/smarter-extension-weather",
    license: "AGPL-3.0",
    docsHtml: "<h3>Weather</h3><p>Current weather, from Open-Meteo.</p>",
    latestVersion: "0.2.0",
    versions: [
      { version: "0.2.0", requiresSmarter: ">=0.27", releasedAt: "2026-10-15T18:00:00Z", compatible: true },
      { version: "0.1.0", requiresSmarter: ">=0.27", releasedAt: "2026-10-15T12:00:00Z", compatible: true },
    ],
    installedVersion: "0.1.0",
    action: "update",
    detailUrl: "/extensions/weather/",
    ...overrides,
  };
}

export const registryResponse: RegistryResponse = {
  enabled: true,
  error: null,
  objects: [
    makeRegistryExtension({
      slug: "calculator",
      displayName: "Calculator",
      description: "Evaluates math expressions exactly.",
      latestVersion: "0.1.0",
      versions: [{ version: "0.1.0", requiresSmarter: ">=0.27", releasedAt: null, compatible: true }],
      installedVersion: "0.1.0",
      action: "installed",
      detailUrl: "/extensions/calculator/",
    }),
    makeRegistryExtension({
      slug: "date-calculator",
      displayName: "Date Calculator",
      description: "Date arithmetic for LLMs.",
      latestVersion: "0.1.0",
      versions: [{ version: "0.1.0", requiresSmarter: ">=0.27", releasedAt: null, compatible: true }],
      installedVersion: null,
      action: "install",
      detailUrl: null,
    }),
    makeRegistryExtension(),
    makeRegistryExtension({
      slug: "stock-quotes",
      displayName: "Stock Quotes",
      description: "Delayed stock quotes.",
      publisher: "Market Data Co",
      publisherUrl: null,
      trustBadge: "community",
      trustBadgeLabel: "Community",
      latestVersion: null,
      versions: [{ version: "2.0.0", requiresSmarter: ">=1.0", releasedAt: null, compatible: false }],
      installedVersion: null,
      action: "incompatible",
      detailUrl: null,
    }),
  ],
};

export const disabledRegistry: RegistryResponse = {
  enabled: false,
  error: "The extension registry is disabled until SMARTER_EXTENSION_REGISTRY_PUBLIC_KEY is set.",
  objects: [],
};

export function makeDetail(overrides: Partial<ExtensionDetail> = {}): ExtensionDetail {
  return {
    ...makeSummary(),
    homepage: "https://github.com/smarter-sh/smarter-extension-weather",
    license: "AGPL-3.0",
    docsHtml: "<h3>Weather</h3><p>Current weather, from Open-Meteo.</p>",
    tools: [
      {
        name: "get_weather",
        functionName: "ext_weather_get_weather",
        description: "Get the current weather, and the forecast for the next 24 hours, for a location.",
        parameters: { type: "object", properties: { location: { type: "string" } }, required: ["location"] },
      },
    ],
    loadError: null,
    settings: [
      {
        name: "google_maps_api_key",
        type: "secret",
        description: "A Google Maps Geocoding API key.",
        required: true,
        default: null,
        choices: null,
        value: null,
        secretId: 7,
        secretName: "google_maps_api_key",
        isSet: true,
      },
      {
        name: "weather_api_url",
        type: "url",
        description: "The Open-Meteo forecast api.",
        required: false,
        default: "https://api.open-meteo.com/v1/forecast",
        choices: null,
        value: null,
        secretId: null,
        secretName: null,
        isSet: false,
      },
      {
        name: "retries",
        type: "integer",
        description: "How many times to retry.",
        required: false,
        default: 2,
        choices: null,
        value: 3,
        secretId: null,
        secretName: null,
        isSet: true,
      },
      {
        name: "verbose",
        type: "boolean",
        description: "Log more.",
        required: false,
        default: false,
        choices: null,
        value: null,
        secretId: null,
        secretName: null,
        isSet: false,
      },
      {
        name: "units",
        type: "choice",
        description: "The default units.",
        required: false,
        default: "METRIC",
        choices: ["METRIC", "USCS"],
        value: null,
        secretId: null,
        secretName: null,
        isSet: false,
      },
    ],
    missingSettings: [],
    versions: [
      {
        id: 12,
        version: "0.1.0",
        sha256: "163741b59ffdb6fdeed1e9c4006378a06991c41a6bd3082ff926bdaf941ef767",
        sourceUrl: "https://github.com/smarter-sh/smarter-extension-weather/releases/download/v0.1.0/weather-0.1.0.zip",
        installedBy: "admin",
        createdAt: "2026-10-15T12:00:00Z",
        isInstalled: true,
      },
      {
        id: 11,
        version: "0.0.9",
        sha256: "0".repeat(64),
        sourceUrl: "",
        installedBy: null,
        createdAt: "2026-10-01T12:00:00Z",
        isInstalled: false,
      },
    ],
    resources: [{ kind: "Secret", name: "weather_example", owner: "admin", version: "0.1.0", managed: true }],
    switches: [{ name: "ext_weather_verbose", description: "Log the raw forecast.", active: false }],
    allAccounts: true,
    accounts: [],
    availableSecrets: [
      { id: 7, name: "google_maps_api_key" },
      { id: 8, name: "openai_api_key" },
    ],
    ...overrides,
  };
}

export const detail = makeDetail();

export const disabledDetail = makeDetail({
  enabled: false,
  updateAvailable: false,
  latestVersion: "0.1.0",
  missingSettings: ["google_maps_api_key"],
  settings: makeDetail().settings.map((setting) =>
    setting.type === "secret" ? { ...setting, isSet: false, secretId: null, secretName: null } : setting,
  ),
});

export const brokenDetail = makeDetail({
  tools: [],
  loadError: "weather 0.1.0 could not be imported: ModuleNotFoundError: No module named 'pandas'",
  error: "weather 0.1.0 was installed, but: post_install failed",
  switches: [],
  resources: [],
  docsHtml: "",
});

export function action(message: string, extension: ExtensionDetail | null = detail): ActionResponse {
  return { message, extension };
}

export const accounts = [
  { id: 1, accountNumber: "3141-5926-5359", companyName: "Smarter" },
  { id: 2, accountNumber: "2718-2818-2845", companyName: "Acme Corp" },
];
