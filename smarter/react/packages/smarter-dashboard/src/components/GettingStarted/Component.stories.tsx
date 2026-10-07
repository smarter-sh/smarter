import type { Meta, StoryObj } from "@storybook/react-vite";

import { appContext, sessionContext } from "@/mocks/fixtures";
import { dashboardErrorHandlers, gettingStartedHandler } from "@/mocks/handlers";

import GettingStarted from "./Component";

/** The steps to get started, until they are all done. */
const meta = {
  title: "Dashboard/GettingStarted",
  component: GettingStarted,
  args: { sessionContext, apiUrl: appContext.gettingStartedApiUrl },
  parameters: { msw: { handlers: [gettingStartedHandler] } },
} satisfies Meta<typeof GettingStarted>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const ApiError: Story = {
  parameters: { msw: { handlers: dashboardErrorHandlers } },
};
