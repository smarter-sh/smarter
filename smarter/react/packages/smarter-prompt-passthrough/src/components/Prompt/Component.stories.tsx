import type { Meta, StoryObj } from "@storybook/react-vite";

import { PROVIDER_API_URL, sessionContext } from "@/mocks/fixtures";
import { passthroughErrorHandlers, passthroughHandlers } from "@/mocks/handlers";

import Prompt from "@/components/Prompt/Component";

/** Send a raw request to an LLM provider's API, through Smarter, and see its response. */
const meta = {
  title: "Prompt Passthrough/Prompt",
  component: Prompt,
  args: { sessionContext, defaultLLMProviderId: 1, defaultTemplateId: 1, providerApiUrl: PROVIDER_API_URL },
  parameters: { layout: "fullscreen", msw: { handlers: passthroughHandlers } },
} satisfies Meta<typeof Prompt>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

/** The provider rejects the request. */
export const ProviderError: Story = {
  parameters: { msw: { handlers: passthroughErrorHandlers } },
};
