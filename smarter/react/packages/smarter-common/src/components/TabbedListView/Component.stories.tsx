import type { Meta, StoryObj } from "@storybook/react-vite";

import { type Example, exampleContext, sessionContext } from "../../mocks/example";
import { listErrorHandlers, listHandlers, manyExamples } from "../../mocks/handlers";
import TabbedListView from "./Component";

const ExampleTabbedListView = TabbedListView<Example>;

/**
 * The tabbed list of every list app: Your and Shared tabs, list and card views, a search, and a
 * pager, which it loads from the app's list api, a page at a time. Shown here with an example
 * object type.
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

/** Several pages of examples, 10 to a page. The search and the pager request them from the list api. */
export const Paginated: Story = {
  parameters: { msw: { handlers: listHandlers(manyExamples(42), manyExamples(12), 10) } },
};

export const ApiError: Story = {
  parameters: { msw: { handlers: listErrorHandlers } },
};
