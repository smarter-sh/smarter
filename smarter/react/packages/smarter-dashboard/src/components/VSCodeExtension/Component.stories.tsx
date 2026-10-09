import type { Meta, StoryObj } from "@storybook/react-vite";

import VSCodeExtension from "@/components/VSCodeExtension/Component";

/** The Smarter VS Code extension. */
const meta = {
  title: "Dashboard/VSCodeExtension",
  component: VSCodeExtension,
} satisfies Meta<typeof VSCodeExtension>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
