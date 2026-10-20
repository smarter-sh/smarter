import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";

import { appContext } from "@/mocks/fixtures";
import { welcomeErrorHandlers, welcomeHandlers } from "@/mocks/handlers";

import App, { OPEN_ATTRIBUTE } from "@/App";

/** The whole app, as the web console renders it, with its api mocked. */
const meta = {
  title: "Welcome/App",
  component: App,
  args: { appContext },
  parameters: { layout: "fullscreen", msw: { handlers: welcomeHandlers } },
} satisfies Meta<typeof App>;

export default meta;
type Story = StoryObj<typeof meta>;

/** A new user's first console page: the dialog opens by itself. */
export const Default: Story = {};

/** A user who has closed the dialog before opens it from the user menu's Welcome Tour item. */
export const OpenedFromTheUserMenu: Story = {
  args: { appContext: { ...appContext, show: false } },
  decorators: [
    (Story) => (
      <>
        <button type="button" {...{ [OPEN_ATTRIBUTE]: "true" }}>
          Welcome Tour
        </button>
        <Story />
      </>
    ),
  ],
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("button", { name: "Welcome Tour" }));
    await expect(await canvas.findByRole("dialog", { name: "Welcome to Smarter, Ada!" })).toBeInTheDocument();
  },
};

export const ApiError: Story = {
  parameters: { msw: { handlers: welcomeErrorHandlers } },
};
