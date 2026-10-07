import type { Meta, StoryObj } from "@storybook/react-vite";

import { appContext, sessionContext } from "@/mocks/fixtures";
import { dashboardErrorHandlers, budgetsHandlers } from "@/mocks/handlers";

import BudgetAlerts from "./Component";

/** Alerts for the budgets that are locked, or nearly spent. */
const meta = {
  title: "Dashboard/BudgetAlerts",
  component: BudgetAlerts,
  args: { sessionContext, apiUrl: appContext.budgetsApiUrl },
  parameters: { msw: { handlers: [...budgetsHandlers] } },
} satisfies Meta<typeof BudgetAlerts>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const ApiError: Story = {
  parameters: { msw: { handlers: dashboardErrorHandlers } },
};
