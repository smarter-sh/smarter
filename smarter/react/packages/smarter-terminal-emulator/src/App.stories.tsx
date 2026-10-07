import type { Meta, StoryObj } from "@storybook/react-vite";

import { STREAM_URL } from "@/mocks/fixtures";
import { streamHandlers } from "@/mocks/handlers";

import App from "./App";

/** The whole app, as the web console renders it, with its log stream mocked. */
const meta = {
  title: "Terminal Emulator/App",
  component: App,
  args: { apiUrl: STREAM_URL },
  parameters: { layout: "fullscreen", msw: { handlers: streamHandlers } },
} satisfies Meta<typeof App>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
