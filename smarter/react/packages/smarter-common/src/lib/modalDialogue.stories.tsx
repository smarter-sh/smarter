import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import { Modal } from "./modalDialogue";

/** The dialog of the list apps' clone, rename and delete actions, and of their results. */
const meta = {
  title: "Common/Modal",
  component: Modal,
  args: { show: true, title: "Delete Secret", onOk: fn(), onCancel: fn() },
} satisfies Meta<typeof Modal>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Confirm: Story = {
  args: { children: "Are you sure you want to delete secret openai_api_key?" },
};

export const Result: Story = {
  args: {
    title: "✅ Success",
    onOk: undefined,
    onCancel: undefined,
    onClose: fn(),
    children: "Successfully deleted secret.",
  },
};
