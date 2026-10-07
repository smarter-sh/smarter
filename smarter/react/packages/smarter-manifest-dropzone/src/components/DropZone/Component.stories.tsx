import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, userEvent, within } from "storybook/test";

import { SECRET_MANIFEST, sessionContext } from "@/mocks/fixtures";
import { applyErrorHandlers, applyHandlers } from "@/mocks/handlers";

import DropZone from "./Component";

/** Apply a manifest by dropping, or choosing, its YAML file. */
const meta = {
  title: "Manifest Dropzone/DropZone",
  component: DropZone,
  args: { sessionContext },
  parameters: { msw: { handlers: applyHandlers } },
} satisfies Meta<typeof DropZone>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

/** Choosing a manifest file applies it, and shows the result. */
export const Applied: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const file = new File([SECRET_MANIFEST], "secret.yaml", { type: "application/yaml" });
    await userEvent.upload(canvas.getByLabelText("Manifest file"), file);
    await expect(await canvas.findByRole("dialog", { name: "Manifest Applied" })).toBeInTheDocument();
  },
};

/** A manifest that the api rejects. */
export const ApplyFailed: Story = {
  parameters: { msw: { handlers: applyErrorHandlers } },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const file = new File([SECRET_MANIFEST], "secret.yaml", { type: "application/yaml" });
    await userEvent.upload(canvas.getByLabelText("Manifest file"), file);
    await expect(await canvas.findByRole("dialog", { name: "Manifest Apply Failed" })).toBeInTheDocument();
  },
};
