import type { Meta, StoryObj } from "@storybook/react-vite";

import { extensionObjects, sessionContext } from "@/mocks/fixtures";

import ExtensionDetailView from "@/components/ExtensionDetailView/Component";

/** The Details tab of an Extension's read-only detail, which opens when a row of the Extensions tab is chosen. */
const meta = {
  title: "LLMTool List/ExtensionDetailView",
  component: ExtensionDetailView,
  args: {
    sessionContext,
    object: extensionObjects[0],
    onRequery: () => {},
  },
} satisfies Meta<typeof ExtensionDetailView>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

/** A disabled, unverified extension, uploaded without a homepage. */
export const Uploaded: Story = {
  args: { object: extensionObjects[1] },
};
