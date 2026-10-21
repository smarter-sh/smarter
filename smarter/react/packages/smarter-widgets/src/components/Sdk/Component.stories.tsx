import type { Meta, StoryObj } from "@storybook/react-vite";

import Sdk from "@/components/Sdk/Component";

/** The Smarter SDKs. */
const meta = {
  title: "Widgets/Sdk",
  component: Sdk,
} satisfies Meta<typeof Sdk>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

/** On a page outside the web console, such as smarter.sh, which links to a platform's OpenAPI document. */
export const OutsideTheWebConsole: Story = {
  args: { openapiUrl: "https://platform.smarter.sh/docs/openapi/", className: "col-12" },
};
