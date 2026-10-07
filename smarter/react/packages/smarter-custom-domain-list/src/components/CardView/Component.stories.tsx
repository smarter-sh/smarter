import type { Meta, StoryObj } from "@storybook/react-vite";

import { ownedObjects, sessionContext } from "@/mocks/fixtures";
import { actionHandlers } from "@/mocks/handlers";

import CardView from "./Component";

const meta = {
  title: "Custom Domain List/CardView",
  component: CardView,
  args: {
    sessionContext,
    objects: ownedObjects,
    onRequery: () => {},
  },
  parameters: { msw: { handlers: actionHandlers } },
} satisfies Meta<typeof CardView>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Empty: Story = {
  args: { objects: [] },
};
