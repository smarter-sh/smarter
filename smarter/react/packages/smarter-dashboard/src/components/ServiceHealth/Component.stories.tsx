import type { Meta, StoryObj } from "@storybook/react-vite";

import { appContext } from "@/mocks/fixtures";
import { dashboardErrorHandlers, serviceHealthHandler } from "@/mocks/handlers";

import ServiceHealth from "./Component";

/** The health of the platform's backend services. */
const meta = {
  title: "Dashboard/ServiceHealth",
  component: ServiceHealth,
  args: { apiUrl: appContext.serviceHealthApiUrl },
  parameters: { msw: { handlers: [serviceHealthHandler] } },
} satisfies Meta<typeof ServiceHealth>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const ApiError: Story = {
  parameters: { msw: { handlers: dashboardErrorHandlers } },
};
