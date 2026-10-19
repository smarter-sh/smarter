import type { Meta, StoryObj } from "@storybook/react-vite";

import Console from "@/components/Console/Component";
import { config, configWithHistory, plainWorkbench, workbench } from "@/mocks/fixtures";
import { tabHandlers } from "@/mocks/handlers";

/** The Console: the LLMClient's configuration, and the chat session's histories, as JSON. */
const meta = {
  title: "Workbench/Console",
  component: Console,
  args: { workbench: plainWorkbench, config },
  parameters: { layout: "fullscreen", msw: { handlers: tabHandlers } },
} satisfies Meta<typeof Console>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

/** A chat session in progress, with tool calls. */
export const WithHistory: Story = {
  args: { config: configWithHistory },
};

/** Before the configuration arrives. */
export const Empty: Story = {
  args: { config: null },
};

/**
 * With the Manifest and Deployment tabs, which fetch their data when they are first opened. Storybook has no log
 * stream, so the Server Logs tab, which is first, keeps connecting.
 */
export const WithEveryTab: Story = {
  args: { workbench: { ...workbench, logStreamUrl: null } },
};
