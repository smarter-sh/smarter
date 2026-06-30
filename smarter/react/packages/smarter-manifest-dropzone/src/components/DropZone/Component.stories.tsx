import type { SessionContext } from "@smarter/common";
import type { Meta, StoryObj } from "@storybook/react";

import DropZone from "./Component";

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


const meta: Meta<typeof DropZone> = {
  title: "Dashboard/DropZone",
  component: DropZone,
  parameters: {
    layout: "fullscreen",
  },
};

export default meta;

type Story = StoryObj<typeof DropZone>;

export const Default: Story = {
  args: {
    sessionContext,
  },
};
