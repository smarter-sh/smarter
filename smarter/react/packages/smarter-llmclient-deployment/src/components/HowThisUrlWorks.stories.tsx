import type { Meta, StoryObj } from "@storybook/react-vite";

import HowThisUrlWorks from "@/components/HowThisUrlWorks";
import { authenticatedPage, notDeployedPage, workbenchPage } from "@/mocks/fixtures";

const meta = {
  title: "LLMClient Deployment/HowThisUrlWorks",
  component: HowThisUrlWorks,
  args: { page: workbenchPage },
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof HowThisUrlWorks>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Public: Story = {};
export const ApiKeyRequired: Story = { args: { page: authenticatedPage } };
export const WithoutExamplePrompts: Story = { args: { page: notDeployedPage } };
