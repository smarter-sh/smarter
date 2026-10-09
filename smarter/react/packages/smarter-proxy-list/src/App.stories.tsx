import type { Meta, StoryObj } from "@storybook/react-vite";

import { sessionContext } from "@/mocks/fixtures";
import { actionHandlers, listErrorHandlers, listHandlers } from "@/mocks/handlers";

import App from "@/App";

/** The whole app, as the web console renders it, with its api mocked. */
const meta = {
  title: "Proxy List/App",
  component: App,
  args: { sessionContext },
  parameters: { layout: "fullscreen", msw: { handlers: [...listHandlers(), ...actionHandlers] } },
} satisfies Meta<typeof App>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Empty: Story = {
  parameters: { msw: { handlers: listHandlers([], []) } },
};

export const ApiError: Story = {
  parameters: { msw: { handlers: listErrorHandlers } },
};
