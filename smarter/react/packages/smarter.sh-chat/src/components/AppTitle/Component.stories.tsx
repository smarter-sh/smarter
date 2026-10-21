import type { Meta, StoryObj } from "@storybook/react-vite";

import AppTitle from "@/components/AppTitle/Component";

/** The chat's title, with icons for the LLMClient's validity and deployment. */
const meta = {
  title: "Smarter Chat/AppTitle",
  component: AppTitle,
  args: { title: "Stackademy v1.0.0", isReady: true, isValid: true, isDeployed: false },
} satisfies Meta<typeof AppTitle>;

export default meta;
type Story = StoryObj<typeof meta>;

/** A valid LLMClient, in the sandbox. */
export const Default: Story = {};

export const Deployed: Story = {
  args: { isDeployed: true },
};

export const NotValid: Story = {
  args: { isValid: false },
};

export const Loading: Story = {
  args: { isReady: false },
};
