import type { Meta, StoryObj } from "@storybook/react-vite";

import { sessionContext } from "@/mocks/fixtures";
import { listHandlers } from "@/mocks/handlers";

import App from "@/App";

/** The whole app, as the web console renders it, with its api mocked. */
const meta = {
  title: "Infrastructure Resource List/App",
  component: App,
  args: { sessionContext },
  parameters: { layout: "fullscreen", msw: { handlers: listHandlers() } },
} satisfies Meta<typeof App>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
