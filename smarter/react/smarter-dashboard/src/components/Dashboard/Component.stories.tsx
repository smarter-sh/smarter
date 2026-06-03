// Dashboard.stories.tsx

import type { Meta, StoryObj } from "@storybook/react";
import type { AppContextInterface } from "@/main";
import Dashboard from "./Component";

const meta: Meta<typeof Dashboard> = {
  title: "Dashboard/Root",
  component: Dashboard,
  parameters: {
    layout: "fullscreen",
  },
  args: {
    appContext: {
      myResourcesApiUrl: "/dashboard/api/my-resources/",
      serviceHealthApiUrl: "/dashboard/api/service-health/",
      csrfCookieName: "csrftoken",
      csrftoken: "dummy-csrf-token",
      djangoSessionCookieName: "sessionid",
      cookieDomain: "localhost",
    } as AppContextInterface,
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
    appContext: {
      myResourcesApiUrl: "/dashboard/api/my-resources/",
      serviceHealthApiUrl: "/dashboard/api/service-health/",
      csrfCookieName: "customcsrftoken",
      csrftoken: "custom-token",
      djangoSessionCookieName: "customsessionid",
      cookieDomain: "localhost",
    } as AppContextInterface,
  },
};
