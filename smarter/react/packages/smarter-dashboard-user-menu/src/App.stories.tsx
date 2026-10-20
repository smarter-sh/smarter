import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";

import { anonymousAppContext, appContext, singleProfileAppContext } from "@/mocks/fixtures";
import { profileImageHandlers, userProfileHandlers } from "@/mocks/handlers";

import App from "@/App";

/** The whole app, as the web console's navbar renders it, with its apis mocked. Each story opens the menu. */
const meta = {
  title: "DashboardUserMenu/App",
  component: App,
  args: { appContext, onSwitched: fn() },
  parameters: { msw: { handlers: [...userProfileHandlers, ...profileImageHandlers] } },
  decorators: [
    (Story) => (
      <div className="d-flex justify-content-end p-5" style={{ minHeight: 480 }}>
        <Story />
      </div>
    ),
  ],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getAllByRole("button")[0]);
  },
} satisfies Meta<typeof App>;

export default meta;
type Story = StoryObj<typeof meta>;

/** A student who is enrolled in two courses: the menu has Change Profile. */
export const Default: Story = {};

/** A user with one profile has no Change Profile item. */
export const SingleProfile: Story = {
  args: { appContext: singleProfileAppContext },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("button", { name: "ada@example.edu" }));
    await expect(canvas.queryByRole("button", { name: "Change Profile" })).not.toBeInTheDocument();
  },
};

/** A superuser's badge. */
export const Superuser: Story = {
  args: { appContext: { ...appContext, user: { ...appContext.user, isSuperuser: true } } },
};

/** An anonymous request: the languages, and Sign In. */
export const Anonymous: Story = {
  args: { appContext: anonymousAppContext },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("button", { name: "Sign In" }));
    await expect(canvas.getByRole("link", { name: "Sign In" })).toBeInTheDocument();
  },
};

/** Change Profile opens the dialog, which lists the user's profiles. */
export const ChangeProfileDialog: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("button", { name: "ada@example.edu" }));
    await userEvent.click(canvas.getByRole("button", { name: "Change Profile" }));
    await expect(await canvas.findByRole("cell", { name: "Building AI Agents" })).toBeInTheDocument();
  },
};
