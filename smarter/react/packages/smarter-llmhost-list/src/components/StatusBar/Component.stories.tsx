import type { Meta, StoryObj } from "@storybook/react-vite";

import { makeObject } from "@/mocks/fixtures";

import { StatusBar } from "./Component";

const meta = {
  title: "LLMHost List/StatusBar",
  component: StatusBar,
  args: { llmhost: makeObject(1) },
} satisfies Meta<typeof StatusBar>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
