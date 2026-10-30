import type { Meta, StoryObj } from "@storybook/react-vite";

import { makeObject, ownedObjects, sessionContext } from "@/mocks/fixtures";
import { actionHandlers } from "@/mocks/handlers";

import DetailView from "@/components/DetailView/Component";

/** The Details tab of an orchestrator's detail, which opens when a row of the list is chosen. */
const meta = {
  title: "Orchestrator List/DetailView",
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

/** An inactive supervisor orchestrator whose critic overrides its LLMClient's temperature. */
export const Supervisor: Story = {
  args: {
    object: makeObject(9, {
      name: "supervised_research",
      strategy: "supervisor",
      maxIterations: 10,
      isActive: false,
      harnesses: [
        { llmClientName: "researcher", role: "executor", executionOrder: 2, isActive: true, config: {} },
        { llmClientName: "lead", role: "planner", executionOrder: 1, isActive: true, config: {} },
        { llmClientName: "reviewer", role: "critic", executionOrder: 3, isActive: false, config: { temperature: 0 } },
      ],
    }),
  },
};

/** An orchestrator without harnesses. */
export const NoHarnesses: Story = {
  args: { object: makeObject(10, { harnesses: [] }) },
};
