import type { Meta, StoryObj } from "@storybook/react-vite";

import GettingStarted from "@/components/GettingStarted";
import { consoleLinks, leafTree, lockedTree } from "@/mocks/fixtures";

/** The next steps, beneath the tree, for an LLMClient that has no Guardrail, no tools, no styles or no api key. */
const meta = {
  title: "LLMClient Architecture/GettingStarted",
  component: GettingStarted,
  args: { tree: leafTree, styled: false, links: consoleLinks },
  decorators: [
    (Story) => (
      <div className="smarter-architecture">
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof GettingStarted>;

export default meta;
type Story = StoryObj<typeof meta>;

/** An unstyled LLMClient that uses nothing: a Guardrail, tools and styles. */
export const Everything: Story = {};

/** A styled LLMClient with a Guardrail: tools only. */
export const ToolsOnly: Story = { args: { tree: lockedTree, styled: true } };
