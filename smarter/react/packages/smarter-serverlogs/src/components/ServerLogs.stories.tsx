import type { Meta, StoryObj } from "@storybook/react-vite";

import { bulkLogs, jsonLog, liveLog } from "@/mocks/fixtures";

import ServerLogs from "@/components/ServerLogs";

const longLine = {
  message: `2026-01-01 12:00:03,000 DEBUG smarter.apps.prompt request body: ${JSON.stringify({
    model: "gpt-4o-mini",
    messages: [{ role: "user", content: "What's the weather in San Francisco? ".repeat(6) }],
  })}`,
};

/**
 * The server logs, as they stream in. Focus the lines, and press ? for the keyboard shortcuts: w wraps,
 * s follows the newest record, / filters, Ctrl+Up and Ctrl+Down move to the top and the bottom.
 */
const meta = {
  title: "Server Logs/ServerLogs",
  component: ServerLogs,
  args: { logs: [...bulkLogs, longLine, jsonLog, liveLog], connected: true, error: null },
  decorators: [
    (Story) => (
      <div className="rounded p-3" style={{ backgroundColor: "#171b20" }}>
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof ServerLogs>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Streaming: Story = {};

/** Before there is a stream, e.g. before the first prompt. */
export const Idle: Story = {
  args: { logs: [], connected: false, idleText: "Send a request to see its server logs here." },
};

export const Disconnected: Story = {
  args: { connected: false, error: "The log stream disconnected. Reconnecting..." },
};
