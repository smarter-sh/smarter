import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";

import { makeObject, sessionContext } from "@/mocks/fixtures";
import { actionHandlers } from "@/mocks/handlers";

import { Toolbar } from "./Component";

const meta = {
  title: "Vectorstore List/Toolbar",
  component: Toolbar,
  args: {
    sessionContext,
    vectorstore: makeObject(1, { name: "first_example" }),
    onRequery: fn(),
  },
  parameters: { msw: { handlers: actionHandlers } },
} satisfies Meta<typeof Toolbar>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

/** One that other resources depend on, or that the user may not delete, cannot be deleted. */
export const CannotDelete: Story = {
  args: { vectorstore: makeObject(3, { name: "in_use_example", canDelete: false }) },
};

/** Deleting: confirm, then the list is queried again. */
export const Delete: Story = {
  play: async ({ args, canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("button", { name: /^Delete:/ }));
    await userEvent.click(await canvas.findByRole("button", { name: "OK" }));
    await expect(await canvas.findByRole("dialog", { name: /Success/ })).toBeInTheDocument();
    await userEvent.click(canvas.getAllByRole("button", { name: "Close" })[0]);
    await expect(args.onRequery).toHaveBeenCalled();
  },
};
