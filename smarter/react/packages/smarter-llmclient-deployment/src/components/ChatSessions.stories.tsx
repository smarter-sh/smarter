import type { Meta, StoryObj } from "@storybook/react-vite";

import ChatSessions from "@/components/ChatSessions";
import { publicPage, workbenchPage } from "@/mocks/fixtures";

const meta = {
  title: "LLMClient Deployment/ChatSessions",
  component: ChatSessions,
  args: { page: workbenchPage },
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof ChatSessions>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Workbench: Story = {};
export const Public: Story = { args: { page: publicPage } };
