import type { Meta, StoryObj } from "@storybook/react-vite";

import { makeObject, ownedObjects, sessionContext } from "@/mocks/fixtures";
import { actionHandlers } from "@/mocks/handlers";

import DetailView from "@/components/DetailView/Component";

/** The Details tab of a vectorstore's detail, which opens when a row of the list is chosen. */
const meta = {
  title: "Vectorstore List/DetailView",
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

/** A managed Pinecone index, with deletion protection, whose provisioning failed. */
export const ManagedFailed: Story = {
  args: {
    object: makeObject(9, {
      name: "pinecone_docs",
      backend: "pinecone",
      hosting: "managed",
      connection: "pinecone_connection",
      apiKeySecret: "pinecone_api_key",
      metric: "dotproduct",
      deletionProtection: true,
      status: "failed",
      statusMessage: "The index could not be created: quota exceeded.",
      vectorCount: 0,
      documentCount: 0,
      snapshotCount: 0,
      stats: { namespaces: { default: { vectorCount: 0 } } },
    }),
  },
};
