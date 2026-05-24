export type TabKey = "user" | "shared";

export type Plugin = {
  id: number;
  name: string;
};

export type User = {
  username: string;
  email: string;
};
export type UserProfile = {
  user: User;
  account?: {
    accountNumber: string;
  };
};

export type Chatbot = {
  id: number;
  isAuthenticationRequired: boolean; // ADD ME PLEASE
  hashedId: string;
  createdAt: string;
  updatedAt: string;
  name: string;
  description: string;
  version: string;
  tags: string[];
  annotations: Array<Record<string, string | boolean>>;
  userProfile: UserProfile;
  functions: any[];
  plugins: Array<Plugin>;
  customDomains: any[];
  apiKeys: any[];
  rfc1034CompliantName: string;
  defaultSystemRole: string;
  baseApiDomain: string;
  baseDefaultHost: string;
  defaultHost: string;
  defaultUrl: string;
  customHost: string | null;
  customUrl: string | null;
  sandboxHost: string;
  sandboxUrl: string;
  hostname: string;
  url: string;
  urlChatbot: string;
  urlChatConfig: string;
  urlChatapp: string;
  urlManifest: string; // ADD ME PLEASE
  ready: boolean;
  deployed: boolean;
  provider: string;
  defaultModel: string;
  defaultTemperature: number;
  defaultMaxTokens: number;
  appName: string;
  appAssistant: string;
  appWelcomeMessage: string;
  appExamplePrompts: string[];
  appPlaceholder: string;
  appInfoUrl: string;
  appBackgroundImageUrl: string | null;
  appLogoUrl: string | null;
  appFileAttachment: boolean;
  dnsVerificationStatus: string;
  tlsCertificateIssuanceStatus: string;
  subdomain: string | null;
  customDomain: string | null;
};

export type PromptListApiResponse = {
  chatbots: {
    user: Chatbot[];
    shared: Chatbot[];
  };
};

export type SessionContext = {
  promptListApiUrl: string;
  csrfCookieName: string;
  csrftoken: string;
  djangoSessionCookieName: string;
  cookieDomain: string;
};
