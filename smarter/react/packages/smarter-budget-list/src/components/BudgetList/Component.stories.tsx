import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";

import { listResponse, sessionContext } from "@/mocks/fixtures";
import { deleteHandlers, listErrorHandlers, listHandlers } from "@/mocks/handlers";

import BudgetList from "./Component";

const meta = {
  title: "Budget List/BudgetList",
  component: BudgetList,
  args: { sessionContext },
  parameters: { msw: { handlers: [...listHandlers(), ...deleteHandlers] } },
} satisfies Meta<typeof BudgetList>;

export default meta;
type Story = StoryObj<typeof meta>;

/** As a superuser sees it: every budget, which they may delete. */
export const Superuser: Story = {};

/** As a user sees it: the budgets that apply to them, which they may not delete. */
export const User: Story = {
  parameters: { msw: { handlers: listHandlers({ ...listResponse, isSuperuser: false }) } },
};

export const NoBudgets: Story = {
  parameters: { msw: { handlers: listHandlers({ ...listResponse, objects: [] }) } },
};

export const ApiError: Story = {
  parameters: { msw: { handlers: listErrorHandlers } },
};

/** A budget's resources, and the budget versus actual chart of one of them. */
export const ResourceChart: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click((await canvas.findAllByRole("button", { name: "Show resources" }))[0]);
    await userEvent.click(canvas.getByRole("button", { name: "Chart" }));
    await expect(await canvas.findByRole("button", { name: "Hide" })).toBeInTheDocument();
  },
};
