import type { Meta, StoryObj } from "@storybook/react-vite";

import Hero from "@/components/Hero";
import { authenticatedPage, notDeployedPage, publicPage, workbenchPage } from "@/mocks/fixtures";

const meta = {
  title: "LLMClient Deployment/Hero",
  component: Hero,
  args: { page: workbenchPage },
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof Hero>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Deployed: Story = {};
export const NotDeployed: Story = { args: { page: notDeployedPage } };
export const ApiKeyRequired: Story = { args: { page: authenticatedPage } };
export const Public: Story = { args: { page: publicPage } };
