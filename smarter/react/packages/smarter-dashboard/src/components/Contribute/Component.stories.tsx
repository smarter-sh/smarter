import type { Meta, StoryObj } from "@storybook/react-vite";

import Contribute from "@/components/Contribute/Component";

/** Contributing to Smarter. */
const meta = {
  title: "Dashboard/Contribute",
  component: Contribute,
} satisfies Meta<typeof Contribute>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
