import type { Meta, StoryObj } from "@storybook/react-vite";

import SelfHost from "@/components/SelfHost/Component";

/** Self-hosting Smarter. */
const meta = {
  title: "Widgets/SelfHost",
  component: SelfHost,
} satisfies Meta<typeof SelfHost>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
