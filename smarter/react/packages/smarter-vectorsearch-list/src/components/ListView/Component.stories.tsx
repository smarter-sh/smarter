import type { Meta, StoryObj } from "@storybook/react-vite";

import { ownedObjects, sessionContext } from "@/mocks/fixtures";
import { actionHandlers } from "@/mocks/handlers";

import ListView from "@/components/ListView/Component";

const meta = {
  title: "Vectorsearch List/ListView",
  component: ListView,
  args: {
    isLoading: false,
    ghostRows: 3,
    sessionContext,
    objects: ownedObjects,
    onRequery: () => {},
  },
  parameters: { msw: { handlers: actionHandlers } },
} satisfies Meta<typeof ListView>;

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
