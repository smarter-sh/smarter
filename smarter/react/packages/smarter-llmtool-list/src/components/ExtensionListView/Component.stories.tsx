import type { Meta, StoryObj } from "@storybook/react-vite";

import { extensionObjects, sessionContext } from "@/mocks/fixtures";

import ExtensionListView from "@/components/ExtensionListView/Component";

const meta = {
  title: "LLMTool List/ExtensionListView",
  component: ExtensionListView,
  args: {
    isLoading: false,
    ghostRows: 3,
    sessionContext,
    objects: extensionObjects,
    onRequery: () => {},
  },
} satisfies Meta<typeof ExtensionListView>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

/** While the list loads, skeleton rows stand in for it. */
export const Loading: Story = {
  args: { isLoading: true, objects: [] },
};

export const Empty: Story = {
  args: { objects: [] },
};
