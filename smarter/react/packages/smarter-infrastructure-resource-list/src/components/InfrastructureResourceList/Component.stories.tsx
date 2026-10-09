import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";

import { manyResources, sessionContext } from "@/mocks/fixtures";
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
    await expect(await canvas.findByText("smarter.sh/vectorstore=qdrant-1", { selector: "span" })).toBeInTheDocument();
    await expect(canvas.queryByText("example.3141-5926-5359.api.example.com A")).not.toBeInTheDocument();
  },
};

/** Only the resources of one type. */
export const ByType: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.selectOptions(await canvas.findByRole("combobox", { name: "Type" }), "kubernetes.node");
    await expect(await canvas.findByText("ip-192-168-1-1.ec2.internal")).toBeInTheDocument();
    await expect(canvas.queryByText("customer.example.com", { selector: "span" })).not.toBeInTheDocument();
  },
};

/** The platform has not recorded any cloud resources. */
export const Empty: Story = {
  parameters: { msw: { handlers: listHandlers([]) } },
};

/** More resources than a page, with the pagination controls. */
export const Paginated: Story = {
  parameters: { msw: { handlers: listHandlers(manyResources) } },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(await canvas.findByRole("button", { name: "Next" }));
    await expect(await canvas.findByText("Showing 51–100 of 120 resources")).toBeInTheDocument();
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
