import type { Meta, StoryObj } from "@storybook/react-vite";

import { appContext, sessionContext } from "@/mocks/fixtures";
import { budgetsHandlers, dashboardErrorHandlers } from "@/mocks/handlers";

import BudgetVsActual from "./BudgetVsActual";

/** The budget versus actual spending of the resources that budgets apply to. */
const meta = {
  title: "Dashboard/BudgetVsActual",
  component: BudgetVsActual,
  args: { sessionContext, apiUrl: appContext.budgetsApiUrl },
  parameters: { msw: { handlers: budgetsHandlers } },
} satisfies Meta<typeof BudgetVsActual>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const ApiError: Story = {
  parameters: { msw: { handlers: dashboardErrorHandlers } },
};
