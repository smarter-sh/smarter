import type { Meta, StoryObj } from "@storybook/react-vite";

import App from "@/App";
import { plainWorkbench, workbench } from "@/mocks/fixtures";
import { workbenchHandlers } from "@/mocks/handlers";

/** The Prompt Engineer's Workbench: the chat, and the Console beside it, with the platform's apis mocked. */
const meta = {
  title: "Workbench/App",
  component: App,
  args: { workbench: { ...workbench, logStreamUrl: null } },
  decorators: [
    (Story) => (
      <div style={{ height: "88vh" }}>
        <Story />
      </div>
    ),
  ],
  parameters: { layout: "fullscreen", msw: { handlers: workbenchHandlers } },
} satisfies Meta<typeof App>;

export default meta;
type Story = StoryObj<typeof meta>;

/** With the Manifest and Deployment tabs. */
export const Default: Story = {};

/** Without the optional tabs. */
export const Plain: Story = { args: { workbench: plainWorkbench } };
