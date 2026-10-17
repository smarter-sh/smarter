import type { Meta, StoryObj } from "@storybook/react-vite";

import { http, HttpResponse } from "msw";

import { appContext, serviceHealth } from "@/mocks/fixtures";
import { dashboardErrorHandlers, serviceHealthHandler } from "@/mocks/handlers";

import ServiceHealth from "@/components/ServiceHealth/Component";

/** The health of the platform's backend services. */
const meta = {
  title: "Dashboard/ServiceHealth",
  component: ServiceHealth,
  args: { sessionContext: appContext.sessionContext, apiUrl: appContext.serviceHealthApiUrl },
  parameters: { msw: { handlers: [serviceHealthHandler] } },
} satisfies Meta<typeof ServiceHealth>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const AllHealthy: Story = {
  parameters: {
    msw: {
      handlers: [
        http.post(appContext.serviceHealthApiUrl, () =>
          HttpResponse.json({
            ...serviceHealth,
            health_checks: serviceHealth.health_checks.map((check) => ({ ...check, healthy: true })),
            health_score: 100,
          }),
        ),
      ],
    },
  },
};

export const ApiError: Story = {
  parameters: { msw: { handlers: dashboardErrorHandlers } },
};
