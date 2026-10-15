/**
 * The types of the Extensions app: the api's contract, generated from the backend's Pydantic models
 * (see src/contract.gen.ts), and the app's own context.
 */
import type { SessionContext } from "@smarter/common";

export type {
  AccountRef,
  AccountsResponse,
  ActionResponse,
  AvailabilityRequest,
  ConfigureRequest,
  ErrorResponse,
  ExtensionDetail,
  ExtensionDetailResponse,
  ExtensionListResponse,
  ExtensionResource,
  ExtensionSetting,
  ExtensionSummary,
  ExtensionSwitch,
  ExtensionTool,
  ExtensionVersionInfo,
  InstallRequest,
  RegistryExtension,
  RegistryResponse,
  RegistryVersionInfo,
  SecretInput,
  SecretRef,
} from "@/contract.gen";

/**
 * What the app knows about the page that hosts it, from its root element's attributes.
 *
 * - session: the Django session and CSRF cookies, and the request headers, for fetchDjangoUrl.
 * - apiUrl: the api's root, e.g. /extensions/react-integration/api/, with a trailing slash.
 * - listUrl: the Extensions list page, e.g. /extensions/.
 * - slug: the extension of a detail page, or undefined on the list page.
 */
export type ConsoleContext = {
  session: SessionContext;
  apiUrl: string;
  listUrl: string;
  slug?: string;
};
