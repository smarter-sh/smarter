import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";

import { listResponse, sessionContext } from "@/mocks/fixtures";
import { listErrorHandlers, listForbiddenHandlers, listHandlers } from "@/mocks/handlers";

import InfrastructureResourceList from "./Component";

const meta = {
  title: "Infrastructure Resource List/InfrastructureResourceList",
  component: InfrastructureResourceList,
  args: { sessionContext },
  parameters: { msw: { handlers: listHandlers() } },
} satisfies Meta<typeof InfrastructureResourceList>;

export default meta;
type Story = StoryObj<typeof meta>;

/** The active resources, as a superuser first sees them. */
export const Active: Story = {};

/** Only the billable resources, of every status. */
export const BillableOnly: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.selectOptions(await canvas.findByRole("combobox", { name: "Status" }), "all");
    await userEvent.click(canvas.getByRole("checkbox", { name: "Billable only" }));
    await expect(canvas.getByText("smarter.sh/vectorstore=qdrant-1", { selector: "span" })).toBeInTheDocument();
    await expect(canvas.queryByText("example.3141-5926-5359.api.example.com A")).not.toBeInTheDocument();
  },
};

/** The platform has not created any cloud resources. */
export const Empty: Story = {
  parameters: {
    msw: { handlers: listHandlers({ summary: { total: 0, active: 0, activeBillable: 0, destroyed: 0 }, objects: [] }) },
  },
};

/** Only the most recent resources are listed. */
export const Truncated: Story = {
  parameters: {
    msw: { handlers: listHandlers({ ...listResponse, summary: { ...listResponse.summary, total: 5000 } }) },
  },
};

/** A user who is not a superuser is refused. */
export const Forbidden: Story = {
  parameters: { msw: { handlers: listForbiddenHandlers } },
};

/** The list cannot be loaded. */
export const LoadError: Story = {
  parameters: { msw: { handlers: listErrorHandlers } },
};
