import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";

import { appContext, sessionContext } from "@/mocks/fixtures";
import { userProfileHandlers, userProfilesErrorHandlers } from "@/mocks/handlers";

import ChangeProfile from "@/components/ChangeProfile/Component";

/** The Change Profile dialog, for a student who is enrolled in two courses. */
const meta = {
  title: "DashboardUserMenu/ChangeProfile",
  component: ChangeProfile,
  args: {
    sessionContext,
    userProfilesApiUrl: appContext.urls.userProfilesApi,
    userProfileSelectApiUrl: appContext.urls.userProfileSelectApi,
    onClose: fn(),
    onSwitched: fn(),
  },
  parameters: { layout: "fullscreen", msw: { handlers: userProfileHandlers } },
} satisfies Meta<typeof ChangeProfile>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole("cell", { name: "1234-5678-9012" })).toBeInTheDocument();
    await expect(canvas.getByText("Current")).toBeInTheDocument();
  },
};

/** Switch chooses the other profile, and the page reloads. */
export const Switch: Story = {
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(await canvas.findByRole("button", { name: "Switch to Building AI Agents" }));
    await expect(args.onSwitched).toHaveBeenCalled();
  },
};

export const LoadError: Story = {
  parameters: { msw: { handlers: userProfilesErrorHandlers } },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await expect(await canvas.findByRole("alert")).toHaveTextContent("Service unavailable");
  },
};
