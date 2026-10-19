import type { Meta, StoryObj } from "@storybook/react-vite";

import App from "@/App";
import { leafArchitecture, lockedArchitecture, stackademyArchitecture } from "@/mocks/fixtures";

/** The whole tab: the introduction, the toolbar, the tree, and the next steps. */
const meta = {
  title: "LLMClient Architecture/App",
  component: App,
  args: { architecture: stackademyArchitecture },
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof App>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * stackademy_sql, styled: a Provider, a SQL plugin, its Connection and their Secrets, a Guardrail, and an Extension.
 * It has everything, so there are no next steps.
 */
export const Stackademy: Story = {};

/** With the Reload button, as the workbench renders it. */
export const WithReload: Story = { args: { onReload: () => {} } };

/** An unstyled LLMClient that uses nothing: the next steps add a Guardrail, a tool and styles. */
export const UsesNothing: Story = { args: { architecture: leafArchitecture } };

/** An unstyled LLMClient that uses another account's Guardrail, which the user can't read. */
export const Locked: Story = { args: { architecture: lockedArchitecture } };
