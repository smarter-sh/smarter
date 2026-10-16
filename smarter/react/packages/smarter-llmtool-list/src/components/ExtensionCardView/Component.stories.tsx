import type { Meta, StoryObj } from "@storybook/react-vite";

import { extensionObjects, sessionContext } from "@/mocks/fixtures";

import ExtensionCardView from "@/components/ExtensionCardView/Component";

const meta = {
  title: "LLMTool List/ExtensionCardView",
  component: ExtensionCardView,
  args: {
    sessionContext,
    objects: extensionObjects,
    onRequery: () => {},
  },
} satisfies Meta<typeof ExtensionCardView>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Empty: Story = {
  args: { objects: [] },
};
