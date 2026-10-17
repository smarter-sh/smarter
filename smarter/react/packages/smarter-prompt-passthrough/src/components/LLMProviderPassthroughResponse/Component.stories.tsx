import type { Meta, StoryObj } from "@storybook/react-vite";

import { completion, providerError, toolCallCompletion } from "@/mocks/fixtures";

import LLMProviderPassthroughResponse from "@/components/LLMProviderPassthroughResponse/Component";

const timing = { elapsedMs: 1240, size: 846 };

/** The provider's HTTP response: none yet, on its way, succeeded or failed. */
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
  args: { apiResponse: { status: 200, statusText: "OK", body: completion, ...timing } },
};

/** The model calls a tool instead of answering. */
export const ToolCalls: Story = {
  args: { apiResponse: { status: 200, statusText: "OK", body: toolCallCompletion, ...timing } },
};

/** The provider rejects the request, and Smarter returns its journaled error. */
export const Failed: Story = {
  args: { apiResponse: { status: 400, statusText: "Bad Request", body: providerError, elapsedMs: 380, size: 2176 } },
};

/** A proxy in front of Smarter answers with HTML. */
export const NotJson: Story = {
  args: {
    apiResponse: {
      status: 502,
      statusText: "Bad Gateway",
      body: "<html><body><h1>502 Bad Gateway</h1></body></html>",
      elapsedMs: 30012,
      size: 52,
    },
  },
};

/** No response arrived. */
export const NetworkError: Story = {
  args: {
    apiResponse: { status: 0, statusText: "", body: { error: { message: "Failed to fetch" } }, elapsedMs: 12, size: 0 },
  },
};
