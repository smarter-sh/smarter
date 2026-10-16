import type { Meta, StoryObj } from "@storybook/react-vite";

import McpServer from "@/components/McpServer/Component";

/** The Smarter Project MCP Server that every platform runs. */
const meta = {
  title: "Dashboard/McpServer",
  component: McpServer,
} satisfies Meta<typeof McpServer>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
