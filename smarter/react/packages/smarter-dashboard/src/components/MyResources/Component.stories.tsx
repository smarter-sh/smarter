import type { Meta, StoryObj } from "@storybook/react-vite";

import { appContext } from "@/mocks/fixtures";
import { dashboardErrorHandlers, myResourcesHandler } from "@/mocks/handlers";

import MyResources from "./Component";

/** The counts of the user's resources. */
const meta = {
  title: "Dashboard/MyResources",
  component: MyResources,
  args: { apiUrl: appContext.myResourcesApiUrl },
  parameters: { msw: { handlers: [myResourcesHandler] } },
} satisfies Meta<typeof MyResources>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const ApiError: Story = {
  parameters: { msw: { handlers: dashboardErrorHandlers } },
};
