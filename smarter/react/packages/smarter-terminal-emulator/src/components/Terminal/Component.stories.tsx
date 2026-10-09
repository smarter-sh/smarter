import type { Meta, StoryObj } from "@storybook/react-vite";

import { STREAM_URL } from "@/mocks/fixtures";
import { streamHandlers } from "@/mocks/handlers";

import TerminalEmulator from "@/components/Terminal/Component";

/** The web console's log terminal, streaming the platform's logs from its api. */
const meta = {
  title: "Terminal Emulator/TerminalEmulator",
  component: TerminalEmulator,
  args: { apiUrl: STREAM_URL },
  parameters: { layout: "fullscreen", msw: { handlers: streamHandlers } },
} satisfies Meta<typeof TerminalEmulator>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
