import type { Meta, StoryObj } from "@storybook/react-vite";

import Problems from "./Component";

/** The manifest's syntax and validation problems, under the editor. */
const meta = {
  title: "Manifest Editor/Problems",
  component: Problems,
  args: { errors: [], isValidating: false, editor: null },
} satisfies Meta<typeof Problems>;

export default meta;
type Story = StoryObj<typeof meta>;

export const NoProblems: Story = {};

export const Validating: Story = {
  args: { isValidating: true },
};

export const WithProblems: Story = {
  args: {
    errors: [
      { source: "sam", message: "value must be at least 32 characters", offset: 120, loc: ["spec", "config", "value"] },
      { source: "yaml", message: "unexpected end of the stream", offset: 200, loc: [] },
    ],
  },
};
