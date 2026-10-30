import type { Meta, StoryObj } from "@storybook/react-vite";

import { makeObject, ownedObjects, sessionContext } from "@/mocks/fixtures";
import { actionHandlers } from "@/mocks/handlers";

import DetailView from "@/components/DetailView/Component";

/** The Details tab of a secret's detail, which opens when a row of the list is chosen. */
const meta = {
  title: "Secret List/DetailView",
  component: DetailView,
  args: {
    sessionContext,
    object: ownedObjects[0],
    onRequery: () => {},
  },
  parameters: { msw: { handlers: actionHandlers } },
} satisfies Meta<typeof DetailView>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

/** A secret that expired, and has never been read. */
export const Expired: Story = {
  args: {
    object: makeObject(9, {
      name: "old_api_key",
      ready: false,
      lastAccessed: null,
      expiresAt: "2026-01-01T00:00:00Z",
      tags: [],
    }),
  },
};
