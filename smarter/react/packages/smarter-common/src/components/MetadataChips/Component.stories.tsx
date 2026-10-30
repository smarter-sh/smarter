import type { Meta, StoryObj } from "@storybook/react-vite";
import { expect, fn, userEvent, within } from "storybook/test";

import { AnnotationsRow, TagsRow } from "./Component";

const filtering = { tags: ["production"], annotations: [], onTag: fn(), onAnnotation: fn() };

/** A row of tag chips in a card view's details table. In a list that can be narrowed by tags, each chip is a button. */
const meta = {
  title: "Common/MetadataChips",
  component: TagsRow,
  args: { tags: ["production", "support", "en"], filtering },
  decorators: [
    (Story) => (
      <table className="table">
        <tbody>
          <Story />
        </tbody>
      </table>
    ),
  ],
} satisfies Meta<typeof TagsRow>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Tags: Story = {
  play: async ({ canvasElement, args }) => {
    await userEvent.click(within(canvasElement).getByRole("button", { name: "support" }));
    await expect(args.filtering?.onTag).toHaveBeenCalledWith("support");
  },
};

export const ReadOnlyTags: Story = { args: { filtering: undefined } };

export const NoTags: Story = { args: { tags: [] } };

export const Annotations: Story = {
  render: () => (
    <AnnotationsRow
      annotations={{
        "acme.com/crm-account-id": "A-10042",
        "smarter.sh/llmclient/use-case": "codebase question answering, with the Smarter Project MCP server",
      }}
      filtering={filtering}
    />
  ),
};
