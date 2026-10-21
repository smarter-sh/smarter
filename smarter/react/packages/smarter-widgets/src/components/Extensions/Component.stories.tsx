import type { Meta, StoryObj } from "@storybook/react-vite";

import Extensions from "@/components/Extensions/Component";

/** Smarter Extensions, installed from the signed registry. */
const meta = {
  title: "Widgets/Extensions",
  component: Extensions,
} satisfies Meta<typeof Extensions>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
