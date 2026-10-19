import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";

import ApiKeys from "@/components/ApiKeys";
import {
  authenticatedPage,
  duplicateNameError,
  inactiveKeyPage,
  session,
  sharedPage,
  workbenchPage,
} from "@/mocks/fixtures";
import { actionHandlers, errorHandlers } from "@/mocks/handlers";

const meta = {
  title: "LLMClient Deployment/ApiKeys",
  component: ApiKeys,
  args: {
    apiKeys: workbenchPage.apiKeys!,
    createApiKeyCommand: workbenchPage.snippets.createApiKeyCommand,
    apiKeysUrl: workbenchPage.links.apiKeysUrl,
    session,
    onPage: fn(),
  },
  parameters: { msw: { handlers: actionHandlers() } },
} satisfies Meta<typeof ApiKeys>;

export default meta;
type Story = StoryObj<typeof meta>;

/** No api key is attached: the url is public. */
export const Public: Story = {};

/** The url requires the attached api key. */
export const Attached: Story = { args: { apiKeys: authenticatedPage.apiKeys! } };

/** The attached api key is turned off. */
export const TurnedOff: Story = { args: { apiKeys: inactiveKeyPage.apiKeys! } };

/** A user who isn't an account admin sees the key, and the command that creates one. */
export const ReadOnly: Story = { args: { apiKeys: sharedPage.apiKeys! } };

/** Creating a key shows its secret, once. */
export const Created: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByLabelText("Name"), "my_new_key");
    await userEvent.click(canvas.getByRole("button", { name: "Create the api key" }));
    await expect(await canvas.findByRole("heading", { name: "Copy its secret now" })).toBeInTheDocument();
  },
};

/** An action that fails explains why. */
export const Failed: Story = {
  parameters: { msw: { handlers: errorHandlers(duplicateNameError) } },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByLabelText("Name"), "my_site_chat");
    await userEvent.click(canvas.getByRole("button", { name: "Create the api key" }));
    await expect(await canvas.findByRole("status")).toHaveTextContent("You already have an api key named");
  },
};
