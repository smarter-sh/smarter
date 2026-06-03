/******************************************************************************
 * LLMProviders function for fetching and displaying LLM providers.
 * This function fetches the list of LLM providers from the specified API endpoint
 * and returns the parsed providers. It handles loading state and errors gracefully.
 * The function uses the AbortController to cancel the fetch request if the function
 * is called again before the fetch completes.
 *****************************************************************************/
import { loggerPrefix } from "@/const";
export interface LLMProvider {
  id: number;
  tags: string[];
  apiKey: {
    id: number;
    name: string;
  };
  isOfficialProvider: boolean;
  tosAccepted: boolean;
  rfc1034CompliantName: string;
  tosAcceptedBy: {
    username: string;
    email: string;
  };
  userProfile: {
    user: {
      username: string;
      email: string;
    };
    account: {
      accountNumber: string;
    };
  };
  createdAt: string;
  updatedAt: string;
  name: string;
  description: string;
  version: string;
  annotations: string[];
  status: string;
  isDefault: boolean;
  isActive: boolean;
  isVerified: boolean;
  isFeatured: boolean;
  isDeprecated: boolean;
  isFlagged: boolean;
  isSuspended: boolean;
  baseUrl: string;
  defaultModel: string;
  connectivityTestPath: string;
  logo: string;
  websiteUrl: string;
  ownershipRequested: string | null;
  contactEmail: string;
  contactEmailVerified: string;
  supportEmail: string;
  supportEmailVerified: string;
  docsUrl: string;
  termsOfServiceUrl: string;
  privacyPolicyUrl: string;
  tosAcceptedAt: string;
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
  return (
    typeof provider.id === "number" &&
    typeof provider.name === "string" &&
    typeof provider.baseUrl === "string"
  );
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
    throw new Error(`Failed to fetch providers: ${response.status}`);
  }

  const data = (await response.json()) as ProvidersApiResponse;
  console.debug(loggerPrefix, `Django fetched response from ${providerApiUrl}:`, data);
  return parseProviders(data);
}

export default LLMProviders;
