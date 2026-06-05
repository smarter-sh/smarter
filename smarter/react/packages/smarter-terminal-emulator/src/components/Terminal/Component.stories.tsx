// Component.stories.tsx

import type { Meta, StoryObj } from "@storybook/react";
import TerminalEmulator from "./Component";

const meta: Meta<typeof TerminalEmulator> = {
  title: "Terminal/Emulator",
  component: TerminalEmulator,
  parameters: {
    layout: "fullscreen",
  },
  args: {
    apiUrl: "/dashboard/logs/api/stream/",
  },
};

export default meta;
type Story = StoryObj<typeof TerminalEmulator>;

export const Default: Story = {
  args: {
    // uses default args above
  },
};

export const WithRemoteApi: Story = {
  args: {
    apiUrl: "https://customer.smarter.sh/dashboard/logs/api/stream/",
  },
};
