import type { Meta, StoryObj } from "@storybook/react-vite";

import { sessionContext } from "@/mocks/fixtures";
import { shellHandlers } from "@/mocks/handlers";

import App from "@/App";

/** The whole app, as the web console renders it, with a pretend shell. */
const meta = {
  title: "Terminal Emulator/App",
  component: App,
  args: { sessionContext },
  parameters: { layout: "fullscreen", msw: { handlers: shellHandlers } },
} satisfies Meta<typeof App>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
