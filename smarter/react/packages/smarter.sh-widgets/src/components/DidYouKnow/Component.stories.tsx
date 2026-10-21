import type { Meta, StoryObj } from "@storybook/react-vite";

import DidYouKnow from "@/components/DidYouKnow/Component";

/** The fact of the day, as a card: the same fact as the note below the web console's title. */
const meta = {
  title: "Widgets/DidYouKnow",
  component: DidYouKnow,
} satisfies Meta<typeof DidYouKnow>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

/** The fact of another day. */
export const AnotherDay: Story = {
  args: { date: new Date("2026-01-01T12:00:00Z") },
};
