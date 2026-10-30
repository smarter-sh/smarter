import type { Meta, StoryObj } from "@storybook/react-vite";

import { makeObject, ownedObjects, sessionContext } from "@/mocks/fixtures";
import { actionHandlers } from "@/mocks/handlers";

import DetailView from "@/components/DetailView/Component";

/** The Details tab of an llmclient's detail, which opens when a row of the list is chosen. */
const meta = {
  title: "LLMClient List/DetailView",
  component: DetailView,
  args: {
    sessionContext,
    object: ownedObjects[0],
    onRequery: () => {},
  },
  parameters: { msw: { handlers: actionHandlers } },
} satisfies Meta<typeof DetailView>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

/** A deployed llmclient, with a verified custom domain, that requires an API key. */
export const Deployed: Story = {
  args: {
    object: makeObject(9, {
      name: "stackademy",
      deployed: true,
      isAuthenticationRequired: true,
      apiKeys: [{ id: 1, apiKey: "00000000-0000-0000-0000-000000000001" }],
      customHost: "chat.example.com",
      customUrl: "https://chat.example.com/",
      customDomain: "example.com",
      customDomains: [{ domainName: "example.com", verificationStatus: "verified" }],
      dnsVerificationStatus: "verified",
      tlsCertificateIssuanceStatus: "issued",
      styles: { appLogoUrl: "https://example.com/logo.png", googleFont: "Roboto" },
    }),
  },
};

/** An llmclient that isn't ready, without tools, styles or allowed origins. */
export const Bare: Story = {
  args: {
    object: makeObject(10, {
      ready: false,
      functions: [],
      plugins: [],
      mcpclients: [],
      guardrails: [],
      tools: [],
      styles: null,
      allowedOrigins: [],
    }),
  },
};
