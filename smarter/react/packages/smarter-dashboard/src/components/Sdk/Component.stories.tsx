import type { Meta, StoryObj } from "@storybook/react-vite";

import Sdk from "./Component";

/** The Smarter SDKs. */
const meta = {
  title: "Dashboard/Sdk",
  component: Sdk,
} satisfies Meta<typeof Sdk>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
