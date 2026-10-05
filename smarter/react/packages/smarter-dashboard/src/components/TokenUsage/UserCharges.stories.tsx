import type { Meta, StoryObj } from "@storybook/react-vite";

import { appContext, sessionContext } from "@/mocks/fixtures";
import { chargesHandler, dashboardErrorHandlers } from "@/mocks/handlers";

import UserCharges from "./UserCharges";

/** The user's token usage over time. */
const meta = {
  title: "Dashboard/UserCharges",
  component: UserCharges,
  args: { sessionContext, apiUrl: appContext.chargesApiUrl },
  parameters: { msw: { handlers: [chargesHandler] } },
} satisfies Meta<typeof UserCharges>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const ApiError: Story = {
  parameters: { msw: { handlers: dashboardErrorHandlers } },
};
