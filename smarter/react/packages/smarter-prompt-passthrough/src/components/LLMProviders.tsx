/******************************************************************************
 * LLMProviders function for fetching and displaying LLM providers.
 * This function fetches the list of LLM providers from the specified API endpoint
 * and returns the parsed providers. It handles loading state and errors gracefully.
 * The function uses the AbortController to cancel the fetch request if the function
 * is called again before the fetch completes.
 *****************************************************************************/
import { loggerPrefix } from "@/const";
import { gettext, interpolate } from "@smarter/common";
/** A user, as the provider api describes one. */
export interface LLMProviderUser {
  username: string;
  email: string;
}

/**
 * An LLM provider, as smarter.apps.provider.serializers.ProviderSerializer returns it, in camelCase.
 * The fields that the Provider model allows to be empty are nullable here too.
 */
export interface LLMProvider {
  id: number;
  tags: string[];
  /** The provider's page in the web console. */
  manifestUrl?: string;
  apiKey: {
    id: number;
    name: string;
    /** The Secret's page in the web console. */
    manifestUrl?: string;
  } | null;
  isOfficialProvider: boolean;
  tosAccepted: boolean;
  rfc1034CompliantName: string;
  tosAcceptedBy: LLMProviderUser | null;
  userProfile: {
    user: LLMProviderUser;
    account: {
      accountNumber: string;
    };
  };
  createdAt: string;
  updatedAt: string;
  name: string;
  description: string;
  version: string;
  /** The provider's annotations, as in Kubernetes: a map of keys to string values, such as { "smarter.sh/purpose": "testing" }. */
  annotations: Record<string, string> | null;
  status: string;
  isDefault: boolean;
  isActive: boolean;
  isVerified: boolean;
  isFeatured: boolean;
  isDeprecated: boolean;
  isFlagged: boolean;
  isSuspended: boolean;
  baseUrl: string;
  defaultModel: string | null;
  connectivityTestPath: string | null;
  logo: string | null;
  websiteUrl: string | null;
  ownershipRequested: string | null;
  contactEmail: string | null;
  contactEmailVerified: string | null;
  supportEmail: string | null;
  supportEmailVerified: string | null;
  docsUrl: string | null;
  termsOfServiceUrl: string | null;
  privacyPolicyUrl: string | null;
  tosAcceptedAt: string | null;
}

interface ProvidersResponse {
  providers: LLMProvider[];
}

type ProvidersApiResponse = ProvidersResponse | LLMProvider[] | LLMProvider;

const isLLMProvider = (candidate: unknown): candidate is LLMProvider => {
  if (!candidate || typeof candidate !== "object") {
    return false;
  }

  const provider = candidate as Partial<LLMProvider>;
  return typeof provider.id === "number" && typeof provider.name === "string" && typeof provider.baseUrl === "string";
};

const parseProviders = (payload: ProvidersApiResponse): LLMProvider[] => {
  if (Array.isArray(payload)) {
    return payload.filter(isLLMProvider);
  }

  if ("providers" in payload && Array.isArray(payload.providers)) {
    return payload.providers.filter(isLLMProvider);
  }

  return isLLMProvider(payload) ? [payload] : [];
};

async function LLMProviders(providerApiUrl: string, signal?: AbortSignal): Promise<LLMProvider[]> {
  const response = await fetch(providerApiUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    signal,
  });

  if (!response.ok) {
    throw new Error(interpolate(gettext("Failed to fetch providers: %(status)s"), { status: response.status }));
  }

  const data = (await response.json()) as ProvidersApiResponse;
  console.debug(loggerPrefix, `Django fetched response from ${providerApiUrl}:`, data);
  return parseProviders(data);
}

export default LLMProviders;
