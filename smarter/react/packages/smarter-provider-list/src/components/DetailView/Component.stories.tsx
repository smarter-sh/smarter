import type { Meta, StoryObj } from "@storybook/react-vite";

import { makeObject, ownedObjects, sessionContext } from "@/mocks/fixtures";
import { actionHandlers } from "@/mocks/handlers";

import DetailView from "@/components/DetailView/Component";

/** The Details tab of a provider's detail, which opens when a row of the list is chosen. */
const meta = {
  title: "Provider List/DetailView",
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

/** A suspended, deprecated provider whose terms of service nobody accepted. */
export const Suspended: Story = {
  args: {
    object: makeObject(9, {
      name: "legacy_provider",
      status: "suspended",
      isActive: false,
      isVerified: false,
      isSuspended: true,
      isDeprecated: true,
      connectivityTestPath: "models/",
      tosAccepted: false,
      tosAcceptedAt: null,
      tosAcceptedBy: null,
    }),
  },
};
