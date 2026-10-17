import type { Meta, StoryObj } from "@storybook/react-vite";

import { sessionContext } from "@/mocks/fixtures";
import { shellHandlers, ticketRefusedHandlers } from "@/mocks/handlers";

import TerminalEmulator from "@/components/Terminal/Component";

/** The web console's terminal: a bash shell in the server's container. Here, a pretend shell answers `hostname`, `whoami`, `pwd`, `ls` and `exit`. */
const meta = {
  title: "Terminal Emulator/TerminalEmulator",
  component: TerminalEmulator,
  args: { sessionContext },
  parameters: { layout: "fullscreen", msw: { handlers: shellHandlers } },
} satisfies Meta<typeof TerminalEmulator>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

/** The ticket api refuses: the terminal is disabled, or the user is not a superuser. */
export const Refused: Story = {
  parameters: { msw: { handlers: ticketRefusedHandlers } },
};
