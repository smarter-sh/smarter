import type { Meta, StoryObj } from "@storybook/react-vite";

import { makeObject, ownedObjects, sessionContext } from "@/mocks/fixtures";
import { actionHandlers } from "@/mocks/handlers";

import DetailView from "@/components/DetailView/Component";

/** The Details tab of a Proxy's detail, which opens when a row of the list is chosen. */
const meta = {
  title: "Proxy List/DetailView",
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

/** An Anthropic Proxy with its own API key, its own headers, and a restricted set of paths. */
export const Restricted: Story = {
  args: {
    object: makeObject(9, {
      name: "anthropic",
      providerName: "anthropic",
      upstreamUrl: "https://api.anthropic.com/v1/",
      apiKeySecret: 7,
      apiKeySecretName: "anthropic_api_key",
      authHeader: "x-api-key",
      authScheme: "",
      headers: { "anthropic-version": "2023-06-01" },
      allowedPaths: ["/messages", "/models/*"],
    }),
  },
};

/** An inactive Proxy without an API key. */
export const InactiveWithoutApiKey: Story = {
  args: {
    object: makeObject(10, { isActive: false, apiKeySecretName: null }),
  },
};
