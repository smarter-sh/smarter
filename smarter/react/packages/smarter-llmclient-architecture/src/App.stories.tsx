import type { Meta, StoryObj } from "@storybook/react-vite";

import App from "@/App";
import { leafTree, lockedTree, stackademyTree } from "@/mocks/fixtures";

/** The whole tab: the introduction, the toolbar, and the tree. */
const meta = {
  title: "LLMClient Architecture/App",
  component: App,
  args: { tree: stackademyTree },
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof App>;

export default meta;
type Story = StoryObj<typeof meta>;

/** stackademy_sql: a Provider, a SQL plugin, its Connection and their Secrets, a Guardrail, and an Extension. */
export const Stackademy: Story = {};

/** With the Reload button, as the workbench renders it. */
export const WithReload: Story = { args: { onReload: () => {} } };

/** An LLMClient that uses nothing. */
export const UsesNothing: Story = { args: { tree: leafTree } };

/** An LLMClient that uses another account's Guardrail, which the user can't read. */
export const Locked: Story = { args: { tree: lockedTree } };
