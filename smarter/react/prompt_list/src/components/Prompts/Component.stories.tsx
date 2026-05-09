// Prompts.stories.tsx

import type { Meta, StoryObj } from "@storybook/react";
import Prompts from "./Component";

const meta: Meta<typeof Prompts> = {
  title: "Prompts/PromptList",
  component: Prompts,
  parameters: {
    layout: "fullscreen",
  },
  args: {
    myResourcesApiUrl: "/workbench/api/",
    csrfCookieName: "csrftoken",
    csrftoken: "dummy-csrf-token",
    djangoSessionCookieName: "sessionid",
    cookieDomain: "localhost",
  },
};

export default meta;
type Story = StoryObj<typeof Prompts>;

export const Default: Story = {
  args: {
    // uses default args above
  },
};

export const WithCustomCookies: Story = {
  args: {
    csrfCookieName: "customcsrftoken",
    csrftoken: "custom-token",
    djangoSessionCookieName: "customsessionid",
    cookieDomain: "localhost",
  },
};
