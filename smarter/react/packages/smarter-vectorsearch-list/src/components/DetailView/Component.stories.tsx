import type { Meta, StoryObj } from "@storybook/react-vite";

import { makeObject, ownedObjects, sessionContext } from "@/mocks/fixtures";
import { actionHandlers } from "@/mocks/handlers";

import DetailView from "@/components/DetailView/Component";

/** The Details tab of a vectorsearch's detail, which opens when a row of the list is chosen. */
const meta = {
  title: "Vectorsearch List/DetailView",
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

/** A disabled vectorsearch that re-ranks with MMR, filters by metadata, and authenticates with a Secret. */
export const Mmr: Story = {
  args: {
    object: makeObject(9, {
      name: "diverse_faq_search",
      isEnabled: false,
      searchType: "mmr",
      fetchK: 20,
      lambdaMult: 0.5,
      metadataFilter: { source: "faq" },
      authSecret: "vectorstore_credentials",
    }),
  },
};

/** A vectorsearch that returns only results above a score threshold. */
export const ScoreThreshold: Story = {
  args: {
    object: makeObject(10, { searchType: "similarity_score_threshold", scoreThreshold: 0.75 }),
  },
};
