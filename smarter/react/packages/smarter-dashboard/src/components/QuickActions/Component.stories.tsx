import type { Meta, StoryObj } from "@storybook/react-vite";

import { appContext, sessionContext } from "@/mocks/fixtures";
import { dashboardErrorHandlers, quickActionsHandler } from "@/mocks/handlers";

import QuickActions from "@/components/QuickActions/Component";

/** Shortcuts to common tasks. */
const meta = {
  title: "Dashboard/QuickActions",
  component: QuickActions,
  args: { sessionContext, apiUrl: appContext.quickActionsApiUrl },
  parameters: { msw: { handlers: [quickActionsHandler] } },
} satisfies Meta<typeof QuickActions>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const ApiError: Story = {
  parameters: { msw: { handlers: dashboardErrorHandlers } },
};
