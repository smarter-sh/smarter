import type { Meta, StoryObj } from "@storybook/react-vite";

import ResourceTree from "./Component";
import { leafTree, lockedTree, stackademyTree } from "../../mocks/resourceTree";

/** An LLMClient's architecture: the tree of the SAM resources that it is built from. */
const meta = {
  title: "Widgets/ResourceTree",
  component: ResourceTree,
  args: { tree: stackademyTree },
} satisfies Meta<typeof ResourceTree>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

/** An LLMClient that uses nothing. */
export const Leaf: Story = { args: { tree: leafTree } };

/** A resource that the user may not read. */
export const Locked: Story = { args: { tree: lockedTree } };

/** Opens with the LLMClient and the resources that it uses directly, as smarter.sh shows it. */
export const Collapsed: Story = { args: { defaultCollapsed: true } };
