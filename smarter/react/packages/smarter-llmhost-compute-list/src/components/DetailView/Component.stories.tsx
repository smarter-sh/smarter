import type { Meta, StoryObj } from "@storybook/react-vite";

import { makeObject, ownedObjects, sessionContext } from "@/mocks/fixtures";
import { actionHandlers } from "@/mocks/handlers";

import DetailView from "@/components/DetailView/Component";

/** The Details tab of an LLMHostCompute's detail, which opens when a row of the list is chosen. */
const meta = {
  title: "LLMHost Compute List/DetailView",
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

/** A CPU node whose node group has not been created yet. */
export const CpuNotCreated: Story = {
  args: {
    object: makeObject(9, {
      name: "cpu_small",
      instanceType: "m6i.large",
      cpu: 2,
      memoryGb: 8,
      gpuType: "",
      gpuCount: 0,
      gpuMemoryGb: 0,
      pricePerHour: null,
      nodegroupStatus: "absent",
      desiredNodes: 0,
      readyNodes: 0,
      llmhostCount: 0,
      lastReconciledAt: null,
    }),
  },
};
