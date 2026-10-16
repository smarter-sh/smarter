import type { Meta, StoryObj } from "@storybook/react-vite";

import { makeExtension } from "@/mocks/fixtures";

import { ExtensionStatusBar } from "@/components/ExtensionStatusBar/Component";

const meta = {
  title: "LLMTool List/ExtensionStatusBar",
  component: ExtensionStatusBar,
  args: { extension: makeExtension(1) },
} satisfies Meta<typeof ExtensionStatusBar>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Disabled: Story = {
  args: {
    extension: makeExtension(2, {
      enabled: false,
      source: "upload",
      trustBadge: "unverified",
      trustBadgeLabel: "Unverified",
    }),
  },
};
