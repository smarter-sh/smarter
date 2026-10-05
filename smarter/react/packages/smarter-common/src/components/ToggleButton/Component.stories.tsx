import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import ToggleButton from "./Component";

/** Switches a list app between its list and card (thumbnail) views. */
const meta = {
  title: "Common/ToggleButton",
  component: ToggleButton,
  args: { viewMode: "list", setViewMode: fn() },
} satisfies Meta<typeof ToggleButton>;

export default meta;
type Story = StoryObj<typeof meta>;

export const List: Story = {};

export const Thumbnail: Story = {
  args: { viewMode: "thumbnail" },
};
