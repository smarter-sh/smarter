import type { Meta, StoryObj } from "@storybook/react-vite";

import SmarterProject, { EndpointsPageNote } from "@/components/SmarterProject";
import { publicPage } from "@/mocks/fixtures";

const meta = {
  title: "LLMClient Deployment/SmarterProject",
  component: SmarterProject,
  args: { page: publicPage },
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof SmarterProject>;

export default meta;
type Story = StoryObj<typeof meta>;

/** The public page's own sections. */
export const Public: Story = {};

/** The workbench's note about the page at the deployed LLMClient's url. */
export const WorkbenchNote: Story = { render: () => <EndpointsPageNote /> };
