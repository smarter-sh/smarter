import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import DocsDialog from "@/components/DocsDialog/Component";

/** The Docs dialog, which SmarterChat opens from its Docs button in sandbox mode. */
const meta = {
  title: "Workbench/DocsDialog",
  component: DocsDialog,
  args: { onClose: fn() },
} satisfies Meta<typeof DocsDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
