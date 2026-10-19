import type { Meta, StoryObj } from "@storybook/react-vite";

import NextSteps from "@/components/NextSteps";
import { sharedPage, workbenchPage } from "@/mocks/fixtures";

const meta = {
  title: "LLMClient Deployment/NextSteps",
  component: NextSteps,
  args: { page: workbenchPage },
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof NextSteps>;

export default meta;
type Story = StoryObj<typeof meta>;

/** The integrations. */
export const Integrations: Story = {};

/** With the clone guide, for a user who may not change the LLMClient. */
export const NotYours: Story = { args: { page: sharedPage } };
