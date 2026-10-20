import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";

import HelpMenu from "@/components/HelpMenu/Component";

/** The Help menu, which the workbench adds to the chat's header: the Docs dialog and the guided tour. */
const meta = {
  title: "Workbench/HelpMenu",
  component: HelpMenu,
  args: { onDocs: fn(), onTour: fn() },
  decorators: [
    (Story) => (
      <div className="cs-conversation-header__actions" style={{ display: "flex", justifyContent: "flex-end" }}>
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof HelpMenu>;

export default meta;
type Story = StoryObj<typeof meta>;

/** Opened: in sandbox mode, the Docs dialog and the guided tour. */
export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("button", { name: "Help" }));
    await expect(canvas.getByRole("button", { name: "Technical references" })).toBeInTheDocument();
  },
};

/** Without the mode switch, or with no Docs dialog: the guided tour only. */
export const TourOnly: Story = {
  args: { onDocs: undefined },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("button", { name: "Help" }));
    await expect(canvas.getByRole("button", { name: "Take the guided tour" })).toBeInTheDocument();
  },
};
