import type { Meta, StoryObj } from "@storybook/react-vite";

import WorkbenchHelp from "./Component";

/** The help callout at the top of each list app, linking to its documentation. */
const meta = {
  title: "Common/WorkbenchHelp",
  component: WorkbenchHelp,
  args: {
    title: "Secrets",
    icon: "ki-book-open",
    docsUrl: "https://docs.smarter.sh/smarter-resources/smarter-secret.html",
    helpText:
      "Smarter Secret is a standard credentials vault, integrated with every other Smarter resource that relies on sensitive information.",
  },
} satisfies Meta<typeof WorkbenchHelp>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
