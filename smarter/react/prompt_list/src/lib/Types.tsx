export type Chatbot = {
  id: number;
  name: string;
  version: string | null;
  createdAt: string;
  updatedAt: string;
  provider: string;
  defaultModel: string | null;
  defaultTemperature: number | null;
  defaultMaxTokens: number | null;
  defaultSystemRole: string | null;
  description: string | null;
  dnsVerificationStatus: string | null;
  appAssistant: string | null;
  appName: string | null;
  appLogoUrl: string | null;
  deployed: boolean;
  isAuthenticationRequired?: boolean;
  tags: string[];
  urlChatbot: string | null;
  userProfile: {
    user: {
      username: string;
      email: string;
    };
  };
  urls: {
    manifest: string;
    chat: string;
    config: string;
  };
};

export type PromptListApiResponse = {
  chatbots: {
    user: Chatbot[];
    shared: Chatbot[];
  };
};

export type ViewMode = "list" | "thumbnail";
