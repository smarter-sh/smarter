import type { Meta, StoryObj } from "@storybook/react-vite";

import { makeObject, ownedObjects, sessionContext } from "@/mocks/fixtures";
import { actionHandlers } from "@/mocks/handlers";

import DetailView from "@/components/DetailView/Component";

/** The Details tab of a custom domain's detail, which opens when a row of the list is chosen. */
const meta = {
  title: "Custom Domain List/DetailView",
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

/** A verified domain that serves a deployed LLMClient. */
export const ServingAnLLMClient: Story = {
  args: {
    object: makeObject(8, {
      name: "chat_domain",
      domainName: "chat.example.com",
      llmclient: {
        id: 1,
        name: "stackademy",
        deployed: true,
        url: "https://stackademy.chat.example.com/",
        sandboxUrl: "/workbench/llm-clients/hashed1/",
        manifestUrl: "/workbench/llm-clients/hashed1/manifest/",
        owner: "admin",
      },
    }),
  },
};

/** A domain whose verification failed, and has no DNS records yet. */
export const Failed: Story = {
  args: {
    object: makeObject(9, {
      name: "broken_domain",
      verificationStatus: "Failed",
      verifiedAt: null,
      verificationMessage: "The domain's NS records do not point to its hosted zone.",
      dnsRecords: [],
    }),
  },
};
