import type { Meta, StoryObj } from "@storybook/react-vite";

import WhatsNew from "./Component";

/** Notable features of recent Smarter releases. */
const meta = {
  title: "Dashboard/WhatsNew",
  component: WhatsNew,
} satisfies Meta<typeof WhatsNew>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
