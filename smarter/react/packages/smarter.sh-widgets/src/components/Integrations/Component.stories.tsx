import type { Meta, StoryObj } from "@storybook/react-vite";

import Integrations from "@/components/Integrations/Component";

/** The Smarter Chat integrations for third-party platforms. */
const meta = {
  title: "Widgets/Integrations",
  component: Integrations,
} satisfies Meta<typeof Integrations>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
