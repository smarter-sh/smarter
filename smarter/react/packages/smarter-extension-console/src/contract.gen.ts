/**
 * The web console's Extensions api contract: generated from contract/extension-console.schema.json by
 * scripts/contract-types.mjs. Do not edit; run `npm run contract:types`.
 */

/**
 * This interface was referenced by `SmarterExtensionConsoleApiContract`'s JSON-Schema
 * via the `definition` "JsonValue".
 */
export type JsonValue = unknown;

/**
 * The requests and responses of the web console's Extensions pages. Generated from smarter.apps.llmtool.extension.contract; do not edit.
 */
export interface SmarterExtensionConsoleApiContract {
  [k: string]: unknown;
}
/**
 * An account, for the extension's availability.
 *
 * This interface was referenced by `SmarterExtensionConsoleApiContract`'s JSON-Schema
 * via the `definition` "AccountRef".
 */
export interface AccountRef {
  accountNumber: string;
  companyName: string;
  id: number;
}
/**
 * Every account, for the availability picker.
 *
 * This interface was referenced by `SmarterExtensionConsoleApiContract`'s JSON-Schema
 * via the `definition` "AccountsResponse".
 */
export interface AccountsResponse {
  objects: AccountRef[];
}
/**
 * The result of an action: what happened, and the extension as it now is, if it still exists.
 *
 * This interface was referenced by `SmarterExtensionConsoleApiContract`'s JSON-Schema
 * via the `definition` "ActionResponse".
 */
export interface ActionResponse {
  extension: ExtensionDetail | null;
  message: string;
}
/**
 * An installed extension, as its detail page shows it.
 *
 * This interface was referenced by `SmarterExtensionConsoleApiContract`'s JSON-Schema
 * via the `definition` "ExtensionDetail".
 */
export interface ExtensionDetail {
  /**
   * The accounts that may use it, when not all accounts may.
   */
  accounts: AccountRef[];
  allAccounts: boolean;
  /**
   * The platform admin's Secrets, for secret settings.
   */
  availableSecrets: SecretRef[];
  description: string;
  /**
   * The url of the extension's detail page.
   */
  detailUrl: string;
  displayName: string;
  /**
   * The extension's documentation, as HTML rendered safely.
   */
  docsHtml: string;
  enabled: boolean;
  /**
   * The last error from loading the extension or running its lifecycle hooks.
   */
  error: string;
  homepage: string | null;
  id: number;
  installedVersion: string | null;
  latestCheckedAt: string | null;
  /**
   * The newest compatible version in the registry.
   */
  latestVersion: string | null;
  license: string | null;
  /**
   * Why the extension's code does not load, if it does not.
   */
  loadError: string | null;
  /**
   * Required settings that block enabling the extension.
   */
  missingSettings: string[];
  /**
   * The publisher's registry id, or an uploaded archive's authors.
   */
  publisher: string;
  resources: ExtensionResource[];
  settings: ExtensionSetting[];
  /**
   * The extension's slug, e.g. weather.
   */
  slug: string;
  source: "registry" | "upload";
  switches: ExtensionSwitch[];
  tools: ExtensionTool[];
  trustBadge: "official" | "verified" | "community" | "unverified";
  /**
   * The badge, as people read it, e.g. Official Smarter Extension.
   */
  trustBadgeLabel: string;
  updateAvailable: boolean;
  versions: ExtensionVersionInfo[];
}
/**
 * A Secret of the platform's admin, which a secret setting can use.
 *
 * This interface was referenced by `SmarterExtensionConsoleApiContract`'s JSON-Schema
 * via the `definition` "SecretRef".
 */
export interface SecretRef {
  id: number;
  name: string;
}
/**
 * A SAM resource that an extension created.
 *
 * This interface was referenced by `SmarterExtensionConsoleApiContract`'s JSON-Schema
 * via the `definition` "ExtensionResource".
 */
export interface ExtensionResource {
  kind: string;
  /**
   * Whether it came from the package's manifests/ directory.
   */
  managed: boolean;
  name: string;
  /**
   * The username of the resource's owner.
   */
  owner: string;
  /**
   * The extension version that created or last applied it.
   */
  version: string;
}
/**
 * One of an extension's settings: its declaration, and its configured value.
 *
 * This interface was referenced by `SmarterExtensionConsoleApiContract`'s JSON-Schema
 * via the `definition` "ExtensionSetting".
 */
export interface ExtensionSetting {
  choices: string[] | null;
  default: string | number | boolean | null;
  description: string;
  /**
   * Whether the setting has a configured value, or a Secret.
   */
  isSet: boolean;
  name: string;
  required: boolean;
  /**
   * The id of a secret setting's Secret.
   */
  secretId: number | null;
  /**
   * The name of a secret setting's Secret.
   */
  secretName: string | null;
  type: "string" | "integer" | "float" | "boolean" | "url" | "choice" | "secret";
  /**
   * The configured value. Always null for a secret setting.
   */
  value: string | number | boolean | null;
}
/**
 * A waffle switch that an extension owns.
 *
 * This interface was referenced by `SmarterExtensionConsoleApiContract`'s JSON-Schema
 * via the `definition` "ExtensionSwitch".
 */
export interface ExtensionSwitch {
  active: boolean;
  description: string;
  /**
   * The switch's full name, e.g. ext_weather_verbose.
   */
  name: string;
}
/**
 * One of an extension's tools, as the LLM sees it.
 *
 * This interface was referenced by `SmarterExtensionConsoleApiContract`'s JSON-Schema
 * via the `definition` "ExtensionTool".
 */
export interface ExtensionTool {
  description: string;
  /**
   * The name the LLM sees, e.g. ext_weather_get_weather.
   */
  functionName: string;
  /**
   * The tool's name in the extension, e.g. get_weather.
   */
  name: string;
  /**
   * The JSON Schema of the tool's arguments.
   */
  parameters: {
    [k: string]: unknown;
  };
}
/**
 * One installed version of an extension.
 *
 * This interface was referenced by `SmarterExtensionConsoleApiContract`'s JSON-Schema
 * via the `definition` "ExtensionVersionInfo".
 */
export interface ExtensionVersionInfo {
  createdAt: string | null;
  id: number;
  /**
   * The username of the superuser who installed it.
   */
  installedBy: string | null;
  /**
   * Whether it is the version that runs.
   */
  isInstalled: boolean;
  sha256: string;
  sourceUrl: string;
  version: string;
}
/**
 * A request to change which accounts may use an extension.
 *
 * This interface was referenced by `SmarterExtensionConsoleApiContract`'s JSON-Schema
 * via the `definition` "AvailabilityRequest".
 */
export interface AvailabilityRequest {
  accountIds?: number[];
  allAccounts: boolean;
}
/**
 * A request to change some of an extension's settings. Settings that are left out don't change.
 *
 * This interface was referenced by `SmarterExtensionConsoleApiContract`'s JSON-Schema
 * via the `definition` "ConfigureRequest".
 */
export interface ConfigureRequest {
  /**
   * Secret settings' values, by name.
   */
  secrets?: {
    [k: string]: SecretInput;
  };
  /**
   * Non-secret settings' values, by name; null resets one to its default.
   */
  values?: {
    [k: string]: string | number | boolean | null;
  };
}
/**
 * The new value of a secret setting: an existing Secret, a value to save in a new one, or neither, to clear it.
 *
 * This interface was referenced by `SmarterExtensionConsoleApiContract`'s JSON-Schema
 * via the `definition` "SecretInput".
 */
export interface SecretInput {
  /**
   * One of the platform admin's Secrets.
   */
  secretId?: number | null;
  /**
   * A value, saved in the Secret extension_<slug>_<setting>.
   */
  value?: string | null;
}
/**
 * Why a request failed.
 *
 * This interface was referenced by `SmarterExtensionConsoleApiContract`'s JSON-Schema
 * via the `definition` "ErrorResponse".
 */
export interface ErrorResponse {
  error: string;
}
/**
 * An extension's detail page.
 *
 * This interface was referenced by `SmarterExtensionConsoleApiContract`'s JSON-Schema
 * via the `definition` "ExtensionDetailResponse".
 */
export interface ExtensionDetailResponse {
  extension: ExtensionDetail;
}
/**
 * The Extensions list: the installed extensions, and the state of the registry.
 *
 * This interface was referenced by `SmarterExtensionConsoleApiContract`'s JSON-Schema
 * via the `definition` "ExtensionListResponse".
 */
export interface ExtensionListResponse {
  objects: ExtensionSummary[];
  /**
   * Whether the registry's public key is configured.
   */
  registryEnabled: boolean;
  /**
   * How many installed extensions have an update in the registry.
   */
  updatesAvailable: number;
}
/**
 * An installed extension, as the Extensions list shows it.
 *
 * This interface was referenced by `SmarterExtensionConsoleApiContract`'s JSON-Schema
 * via the `definition` "ExtensionSummary".
 */
export interface ExtensionSummary {
  description: string;
  /**
   * The url of the extension's detail page.
   */
  detailUrl: string;
  displayName: string;
  enabled: boolean;
  /**
   * The last error from loading the extension or running its lifecycle hooks.
   */
  error: string;
  id: number;
  installedVersion: string | null;
  latestCheckedAt: string | null;
  /**
   * The newest compatible version in the registry.
   */
  latestVersion: string | null;
  /**
   * The publisher's registry id, or an uploaded archive's authors.
   */
  publisher: string;
  /**
   * The extension's slug, e.g. weather.
   */
  slug: string;
  source: "registry" | "upload";
  trustBadge: "official" | "verified" | "community" | "unverified";
  /**
   * The badge, as people read it, e.g. Official Smarter Extension.
   */
  trustBadgeLabel: string;
  updateAvailable: boolean;
}
/**
 * A request to install, or update, an extension from the registry.
 *
 * This interface was referenced by `SmarterExtensionConsoleApiContract`'s JSON-Schema
 * via the `definition` "InstallRequest".
 */
export interface InstallRequest {
  slug: string;
  /**
   * The version; the newest compatible version if null.
   */
  version?: string | null;
}
/**
 * An extension in the registry, as the Browse tab shows it.
 *
 * This interface was referenced by `SmarterExtensionConsoleApiContract`'s JSON-Schema
 * via the `definition` "RegistryExtension".
 */
export interface RegistryExtension {
  action: "install" | "update" | "installed" | "uploaded" | "incompatible";
  description: string;
  /**
   * The installed extension's detail page, if it is installed.
   */
  detailUrl: string | null;
  displayName: string;
  /**
   * The extension's documentation, as HTML rendered safely.
   */
  docsHtml: string;
  homepage: string | null;
  installedVersion: string | null;
  /**
   * The newest version compatible with this platform.
   */
  latestVersion: string | null;
  license: string | null;
  /**
   * The publisher's name.
   */
  publisher: string;
  publisherUrl: string | null;
  slug: string;
  trustBadge: "official" | "verified" | "community" | "unverified";
  trustBadgeLabel: string;
  /**
   * Every released version, newest first.
   */
  versions: RegistryVersionInfo[];
}
/**
 * A released version of a registry extension.
 *
 * This interface was referenced by `SmarterExtensionConsoleApiContract`'s JSON-Schema
 * via the `definition` "RegistryVersionInfo".
 */
export interface RegistryVersionInfo {
  /**
   * Whether it works with this platform's Smarter version.
   */
  compatible: boolean;
  releasedAt: string | null;
  requiresSmarter: string | null;
  version: string;
}
/**
 * A request for the registry's extensions.
 *
 * This interface was referenced by `SmarterExtensionConsoleApiContract`'s JSON-Schema
 * via the `definition` "RegistryRequest".
 */
export interface RegistryRequest {
  /**
   * Whether to download the index again, rather than read the cache.
   */
  refresh?: boolean;
}
/**
 * The registry's extensions, or why they cannot be listed.
 *
 * This interface was referenced by `SmarterExtensionConsoleApiContract`'s JSON-Schema
 * via the `definition` "RegistryResponse".
 */
export interface RegistryResponse {
  /**
   * Whether the registry's public key is configured.
   */
  enabled: boolean;
  /**
   * Why the registry cannot be read, if it cannot.
   */
  error: string | null;
  objects: RegistryExtension[];
}
/**
 * A request to make an earlier version the one that runs.
 *
 * This interface was referenced by `SmarterExtensionConsoleApiContract`'s JSON-Schema
 * via the `definition` "RollbackRequest".
 */
export interface RollbackRequest {
  versionId: number;
}
