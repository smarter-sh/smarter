import type { Meta, StoryObj } from "@storybook/react-vite";

import { providers, sparseProvider, suspendedProvider } from "@/mocks/fixtures";

import LLMProviderMetaData from "@/components/LLMProviderMetaData/Component";

/** The selected provider's card: its identity and links, its flags, and its details. */
const meta = {
  title: "Prompt Passthrough/ProviderMetaData",
  component: LLMProviderMetaData,
  args: { provider: providers[0] },
} satisfies Meta<typeof LLMProviderMetaData>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

/** A provider without a logo, links, API key, contacts or accepted terms. */
export const Sparse: Story = {
  args: { provider: sparseProvider },
};

/** A provider that was flagged and suspended, and whose ownership someone requested. */
export const Suspended: Story = {
  args: { provider: suspendedProvider },
};
