// Dashboard.stories.tsx

import type { Meta, StoryObj } from "@storybook/react";
import Dashboard from "./Component";

const meta: Meta<typeof Dashboard> = {
  title: "Dashboard/Root",
  component: Dashboard,
  parameters: {
    layout: "fullscreen",
  },
  args: {
    myResourcesApiUrl: "/dashboard/api/my-resources/",
    serviceHealthApiUrl: "/dashboard/api/service-health/",
    csrfCookieName: "csrftoken",
    csrftoken: "dummy-csrf-token",
    djangoSessionCookieName: "sessionid",
    cookieDomain: "localhost",
  },
};

export default meta;
type Story = StoryObj<typeof Dashboard>;

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
