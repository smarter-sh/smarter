import type { Meta, StoryObj } from "@storybook/react-vite";

import { makeObject, ownedObjects, sessionContext } from "@/mocks/fixtures";
import { actionHandlers } from "@/mocks/handlers";

import DetailView from "@/components/DetailView/Component";

/** The Details tab of a guardrail's detail, which opens when a row of the list is chosen. */
const meta = {
  title: "Guardrail List/DetailView",
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

/** A guardrail that only monitors, detects with a regular expression, and blocks with a message. */
export const RegexMonitor: Story = {
  args: {
    object: makeObject(9, {
      name: "no_card_numbers",
      mode: "monitor",
      isActive: false,
      strategy: "regex",
      pattern: "\\b(?:\\d[ -]*?){13,16}\\b",
      config: null,
      action: "block",
      replacement: null,
      message: "Please don't share card numbers.",
    }),
  },
};
