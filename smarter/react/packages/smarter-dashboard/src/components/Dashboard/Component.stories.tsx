import type { Meta, StoryObj } from "@storybook/react-vite";

import { appContext } from "@/mocks/fixtures";
import { dashboardErrorHandlers, dashboardHandlers } from "@/mocks/handlers";

import Dashboard from "@/components/Dashboard/Component";

/** The web console's dashboard, with its api mocked. */
const meta = {
  title: "Dashboard/Dashboard",
  component: Dashboard,
  args: { appContext },
  parameters: { layout: "fullscreen", msw: { handlers: dashboardHandlers } },
} satisfies Meta<typeof Dashboard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

/** Every api fails: each widget shows its own error, and the others still render. */
export const ApiErrors: Story = {
  parameters: { msw: { handlers: dashboardErrorHandlers } },
};
