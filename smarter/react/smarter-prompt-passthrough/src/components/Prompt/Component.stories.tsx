// Component.stories.tsx

import type { Meta, StoryObj } from "@storybook/react";
import Prompt from "./Component";

const meta: Meta<typeof Prompt> = {
  title: "Prompt/Passthrough",
  component: Prompt,
  parameters: {
    layout: "fullscreen",
  },
  args: {
    apiUrl: "http://localhost:9357/api/v1/prompts/passthrough/",
    csrfCookieName: "csrftoken",
    djangoSessionCookieName: "sessionid",
    cookieDomain: "localhost",
    defaultLLMProviderId: "1",
    defaultTemplateId: "1",
    providerApiUrl: "/dashboard/passthrough/api/providers/",
  },
};

export default meta;
type Story = StoryObj<typeof Prompt>;

export const Default: Story = {
  args: {
    // uses default args above
  },
};

export const WithDifferentProvider: Story = {
  args: {
    defaultLLMProviderId: "2",
  },
};
