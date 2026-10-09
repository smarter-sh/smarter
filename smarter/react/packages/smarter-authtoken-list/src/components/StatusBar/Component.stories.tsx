import type { Meta, StoryObj } from "@storybook/react-vite";

import { makeObject } from "@/mocks/fixtures";

import { StatusBar } from "@/components/StatusBar/Component";

const meta = {
  title: "AuthToken List/StatusBar",
  component: StatusBar,
  args: { authtoken: makeObject(1) },
} satisfies Meta<typeof StatusBar>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
