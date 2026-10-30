import type { Meta, StoryObj } from "@storybook/react-vite";

import ResourceCard from "./ResourceCard";
import { leafTree, lockedTree, stackademyTree } from "../../mocks/resourceTree";

/** One resource of the tree. */
const meta = {
  title: "Widgets/ResourceCard",
  component: ResourceCard,
  args: { node: stackademyTree.children[3] },
  decorators: [
    (Story) => (
      <div className="smarter-architecture">
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof ResourceCard>;

export default meta;
type Story = StoryObj<typeof meta>;

/** A plugin, which opens its manifest in a new tab. */
export const Plugin: Story = {};

/** The LLMClient, at the root of the tree. */
export const Root: Story = { args: { node: leafTree, isRoot: true } };

/** A resource that the user can't read. */
export const Locked: Story = { args: { node: lockedTree.children[0] } };
