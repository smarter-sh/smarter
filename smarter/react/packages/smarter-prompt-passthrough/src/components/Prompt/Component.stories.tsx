import type { Meta, StoryObj } from "@storybook/react";

import Prompt from "./Component";
import type { SessionContext } from "@smarter/common";

const sessionContext: SessionContext = {
  ApiUrl: "https://customer.smarter.sh/api/llm/",
  csrfCookieName: "csrftoken",
  djangoSessionCookieName: "sessionid",
  cookieDomain: ".smarter.sh",
  debugMode: false,
  smarterClient: "storybook-client",
  smarterClientVersion: "1.0.0",
  smarterRequestId: "storybook-request-id",
  smarterCapabilities: [],
};

const meta: Meta<typeof Prompt> = {
  title: "LLM/Prompt",
  component: Prompt,
  parameters: {
    layout: "fullscreen",
  },
};

export default meta;

type Story = StoryObj<typeof Prompt>;

export const Default: Story = {
  args: {
    sessionContext,
    defaultLLMProviderId: 1,
    defaultTemplateId: 1,
    providerApiUrl: "https://customer.smarter.sh/api/llm/providers/",
  },
};
