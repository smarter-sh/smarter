import type { Meta, StoryObj } from "@storybook/react-vite";

import Cli from "@/components/Cli/Component";

/** The smarter command line interface. */
const meta = {
  title: "Dashboard/Cli",
  component: Cli,
} satisfies Meta<typeof Cli>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
