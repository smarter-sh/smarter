import type { SessionContext } from "@smarter/common";
import type { Meta, StoryObj } from "@storybook/react";

import Dashboard from "./Component";
import type { AppContextInterface } from "@/main";
const sessionContext: SessionContext = {
    ApiUrl: "https://customer.smarter.sh/dashboard/api/my-resources",
    csrfCookieName: "csrftoken",
    djangoSessionCookieName: "sessionid",
    cookieDomain: ".smarter.sh",
    debugMode: false,
    smarterClient: "storybook-client",
    smarterClientVersion: "1.0.0",
    smarterRequestId: "storybook-request-id",
    smarterCapabilities: [],
};

const appContext: AppContextInterface = {
  myResourcesApiUrl: "https://customer.smarter.sh/dashboard/api/my-resources",
  serviceHealthApiUrl: "https://customer.smarter.sh/dashboard/api/service-health",
  sessionContext: sessionContext,
};

const meta: Meta<typeof Dashboard> = {
  title: "Dashboard/Dashboard",
  component: Dashboard,
  parameters: {
    layout: "fullscreen",
  },
};

export default meta;

type Story = StoryObj<typeof Dashboard>;

export const Default: Story = {
  args: {
    appContext,
  },
};
