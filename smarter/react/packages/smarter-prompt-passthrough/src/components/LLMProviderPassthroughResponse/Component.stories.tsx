import type { Meta, StoryObj } from "@storybook/react-vite";

import { completion } from "@/mocks/fixtures";

import LLMProviderPassthroughResponse from "@/components/LLMProviderPassthroughResponse/Component";

/** The provider's HTTP response: ready, working, succeeded or failed. */
const meta = {
  title: "Prompt Passthrough/Response",
  component: LLMProviderPassthroughResponse,
  args: { isProcessing: false, apiResponse: null },
} satisfies Meta<typeof LLMProviderPassthroughResponse>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Ready: Story = {};

export const Sending: Story = {
  args: { isProcessing: true },
};

export const Succeeded: Story = {
  args: { apiResponse: { status: 200, body: completion } },
};

export const Failed: Story = {
  args: { apiResponse: { status: 401, body: { error: { message: "Invalid API key" } } } },
};
