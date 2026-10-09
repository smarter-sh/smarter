import type { Meta, StoryObj } from "@storybook/react-vite";

import { appContext, sessionContext } from "@/mocks/fixtures";
import { dashboardErrorHandlers, activityHandler } from "@/mocks/handlers";

import RecentActivity from "@/components/RecentActivity/Component";

/** The user's latest manifest commands. */
const meta = {
  title: "Dashboard/RecentActivity",
  component: RecentActivity,
  args: { sessionContext, apiUrl: appContext.activityApiUrl },
  parameters: { msw: { handlers: [activityHandler] } },
} satisfies Meta<typeof RecentActivity>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const ApiError: Story = {
  parameters: { msw: { handlers: dashboardErrorHandlers } },
};
