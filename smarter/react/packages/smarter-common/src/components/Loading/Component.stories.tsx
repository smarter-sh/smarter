import type { Meta, StoryObj } from "@storybook/react-vite";

import { Loading } from "./Component";

/** The spinner shown while data loads. */
const meta = {
  title: "Common/Loading",
  component: Loading,
} satisfies Meta<typeof Loading>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
