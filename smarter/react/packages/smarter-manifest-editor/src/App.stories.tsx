import type { Meta, StoryObj } from "@storybook/react-vite";

import { SECRET_IN_USE_YAML, appProps } from "@/mocks/fixtures";
import { cliHandlers, invalidHandler } from "@/mocks/handlers";

import App from "@/App";

/** Edit, validate, save, clone and delete a resource's manifest. */
const meta = {
  title: "Manifest Editor/App",
  component: App,
  args: appProps,
  parameters: { layout: "fullscreen", msw: { handlers: cliHandlers } },
} satisfies Meta<typeof App>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

/** The manifest's SAM model rejects one of its values. */
export const WithProblems: Story = {
  parameters: { msw: { handlers: [invalidHandler, ...cliHandlers] } },
};

/** Other resources depend on this one, so it cannot be deleted. */
export const InUse: Story = {
  args: { initialManifest: SECRET_IN_USE_YAML },
};
