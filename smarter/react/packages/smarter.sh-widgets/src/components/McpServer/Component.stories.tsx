import type { Meta, StoryObj } from "@storybook/react-vite";

import McpServer from "@/components/McpServer/Component";

/** The Smarter Project MCP Server that every platform runs. */
const meta = {
  title: "Widgets/McpServer",
  component: McpServer,
} satisfies Meta<typeof McpServer>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

/** On a page outside the web console, such as smarter.sh, which shows a platform's MCP server. */
export const OutsideTheWebConsole: Story = {
  args: { serverUrl: "https://platform.smarter.sh/api/v1/mcp/smarter-project/" },
};
