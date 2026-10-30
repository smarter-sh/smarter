import type { Meta, StoryObj } from "@storybook/react-vite";

import { makeObject, ownedObjects, sessionContext } from "@/mocks/fixtures";
import { actionHandlers } from "@/mocks/handlers";

import DetailView from "@/components/DetailView/Component";

/** The Details tab of an LLMHost's detail, which opens when a row of the list is chosen. */
const meta = {
  title: "LLMHost List/DetailView",
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

/** An embedding model whose deployment failed, behind a public URL and an API key. */
export const FailedEmbedding: Story = {
  args: {
    object: makeObject(9, {
      name: "bge_embeddings",
      modelRepository: "BAAI/bge-large-en-v1.5",
      modelTask: "embedding",
      servedModelName: "bge-large-en",
      embeddingDimensions: 1024,
      contextWindow: 512,
      supportsStreaming: false,
      supportsFunctionCalling: false,
      inferenceEngine: "tei",
      apiFormat: "huggingface",
      apiKeySecret: 7,
      status: "error",
      statusMessage: "The pod could not pull its image.",
      isActive: false,
      ready: false,
      readyReplicas: 0,
      publicUrl: "https://bge.example.com",
      lastHealthOk: false,
    }),
  },
};
