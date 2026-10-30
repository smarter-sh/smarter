import type { Meta, StoryObj } from "@storybook/react-vite";

import { makeObject, ownedObjects, sessionContext } from "@/mocks/fixtures";
import { actionHandlers } from "@/mocks/handlers";

import DetailView from "@/components/DetailView/Component";

/** The Details tab of an MCPClient's detail, which opens when a row of the list is chosen. */
const meta = {
  title: "MCPClient List/DetailView",
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

/** An inactive MCPClient whose last connection failed, without authentication, and limited to some tools. */
export const ConnectionError: Story = {
  args: {
    object: makeObject(9, {
      name: "flaky_server",
      isActive: false,
      status: "error",
      authType: "none",
      headers: { "X-Client": "smarter" },
      allowedTools: ["search_*"],
      allowedResources: ["docs://*"],
      lastError: "Connection refused",
    }),
  },
};
