import type { Meta, StoryObj } from "@storybook/react-vite";

import { makeObject, ownedObjects, sessionContext } from "@/mocks/fixtures";
import { actionHandlers } from "@/mocks/handlers";

import DetailView from "@/components/DetailView/Component";

/** The Details tab of a connection's detail, which opens when a row of the list is chosen. */
const meta = {
  title: "Connection List/DetailView",
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

/** A connection to a REST API, which is not ready. */
export const ApiConnection: Story = {
  args: {
    object: makeObject(9, { name: "weather_api", kind: "ApiConnection", ready: false, tags: [] }),
  },
};
