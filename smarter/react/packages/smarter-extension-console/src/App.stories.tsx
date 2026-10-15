import type { Meta, StoryObj } from "@storybook/react-vite";

import App from "@/App";
import {
  brokenDetail,
  detailContext,
  disabledDetail,
  disabledRegistry,
  listContext,
  listResponse,
} from "@/mocks/fixtures";
import { detailHandlers, errorHandlers, listHandlers } from "@/mocks/handlers";

/** The whole app, as the web console renders it, with its api mocked. */
const meta = {
  title: "Extension Console/App",
  component: App,
  args: { context: listContext },
  parameters: { layout: "fullscreen", msw: { handlers: listHandlers() } },
} satisfies Meta<typeof App>;

export default meta;
type Story = StoryObj<typeof meta>;

/** The Extensions list. */
export const ExtensionList: Story = {};

/** No extensions are installed, and the registry is disabled. */
export const NothingInstalled: Story = {
  parameters: {
    msw: { handlers: listHandlers({ ...listResponse, objects: [], registryEnabled: false }, disabledRegistry) },
  },
};

/** An extension's page, with an update. */
export const ExtensionPage: Story = {
  args: { context: detailContext },
  parameters: { msw: { handlers: detailHandlers() } },
};

/** A new extension, which needs its secret setting before it can be enabled. */
export const NeedsSettings: Story = {
  args: { context: detailContext },
  parameters: { msw: { handlers: detailHandlers(disabledDetail) } },
};

/** An extension whose code no longer loads. */
export const Broken: Story = {
  args: { context: detailContext },
  parameters: { msw: { handlers: detailHandlers(brokenDetail) } },
};

/** The api fails. */
export const ApiError: Story = {
  parameters: { msw: { handlers: errorHandlers } },
};
