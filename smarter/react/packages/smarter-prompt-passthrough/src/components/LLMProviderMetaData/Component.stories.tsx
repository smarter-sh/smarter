import type { Meta, StoryObj } from "@storybook/react-vite";

import { providers } from "@/mocks/fixtures";

import LLMProviderMetaData from "@/components/LLMProviderMetaData/Component";

/** The selected provider's details, flags and links. */
const meta = {
  title: "Prompt Passthrough/ProviderMetaData",
  component: LLMProviderMetaData,
  args: { provider: providers[0] },
} satisfies Meta<typeof LLMProviderMetaData>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
