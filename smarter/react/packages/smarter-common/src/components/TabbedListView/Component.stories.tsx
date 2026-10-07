import type { Meta, StoryObj } from "@storybook/react-vite";

import { type Example, exampleContext, sessionContext } from "../../mocks/example";
import { listErrorHandlers, listHandlers } from "../../mocks/handlers";
import TabbedListView from "./Component";

const ExampleTabbedListView = TabbedListView<Example>;

/**
 * The tabbed list of every list app: Your and Shared tabs, list and card views, which it loads
 * from the app's list api. Shown here with an example object type.
 */
const meta = {
  title: "Common/TabbedListView",
  component: ExampleTabbedListView,
  args: { sessionContext, tabbedListViewContext: exampleContext },
  parameters: { msw: { handlers: listHandlers() } },
} satisfies Meta<typeof ExampleTabbedListView>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Empty: Story = {
  parameters: { msw: { handlers: listHandlers([], []) } },
};

export const ApiError: Story = {
  parameters: { msw: { handlers: listErrorHandlers } },
};
