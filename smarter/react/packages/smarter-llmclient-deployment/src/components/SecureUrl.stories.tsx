import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import SecureUrl from "@/components/SecureUrl";
import { authenticatedPage, publicPage, session, workbenchPage } from "@/mocks/fixtures";
import { actionHandlers } from "@/mocks/handlers";

const meta = {
  title: "LLMClient Deployment/SecureUrl",
  component: SecureUrl,
  args: { page: workbenchPage, session, onPage: fn() },
  parameters: { layout: "fullscreen", msw: { handlers: actionHandlers() } },
} satisfies Meta<typeof SecureUrl>;

export default meta;
type Story = StoryObj<typeof meta>;

/** The workbench manages the api key in place. */
export const Workbench: Story = {};

/** The url already requires an api key. */
export const ApiKeyRequired: Story = { args: { page: authenticatedPage } };

/** The public page explains the commands and the manifest. */
export const Public: Story = { args: { page: publicPage, session: null } };
