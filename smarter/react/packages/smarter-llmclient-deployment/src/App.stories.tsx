import type { Meta, StoryObj } from "@storybook/react-vite";

import App from "@/App";
import {
  authenticatedPage,
  notDeployedPage,
  publicContext,
  session,
  sharedPage,
  workbenchContext,
} from "@/mocks/fixtures";
import { actionHandlers } from "@/mocks/handlers";

/** The whole page, as Django renders it, with the workbench's api key actions mocked. */
const meta = {
  title: "LLMClient Deployment/App",
  component: App,
  args: { context: workbenchContext },
  parameters: { layout: "fullscreen", msw: { handlers: actionHandlers() } },
} satisfies Meta<typeof App>;

export default meta;
type Story = StoryObj<typeof meta>;

/** The workbench's "Deployment" tab, of a deployed LLMClient that the user owns. */
export const Workbench: Story = {};

/** The page at the deployed LLMClient's url, which anyone can open. */
export const Public: Story = { args: { context: publicContext } };

/** An LLMClient that isn't deployed yet. */
export const NotDeployed: Story = { args: { context: { page: notDeployedPage, session } } };

/** An LLMClient whose url requires an api key. */
export const ApiKeyRequired: Story = { args: { context: { page: authenticatedPage, session } } };

/** An LLMClient that another user shares with a user who isn't an account admin. */
export const SharedWithYou: Story = { args: { context: { page: sharedPage, session } } };
