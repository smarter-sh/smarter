import type { Meta, StoryObj } from "@storybook/react-vite";

import ManifestSection from "@/components/ManifestSection";
import { notDeployedPage, publicPage, workbenchPage } from "@/mocks/fixtures";

const meta = {
  title: "LLMClient Deployment/ManifestSection",
  component: ManifestSection,
  args: { page: workbenchPage },
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof ManifestSection>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Workbench: Story = {};
export const Public: Story = { args: { page: publicPage } };
export const WithoutManifest: Story = { args: { page: notDeployedPage } };
