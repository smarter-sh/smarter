import type { Meta, StoryObj } from "@storybook/react-vite";
import { fn } from "storybook/test";

import SortableHeader from "./Component";

/**
 * A list view's column header. When the list api can sort by its column, clicking it requests the
 * list sorted by that column: ascending, then descending, then in the default order.
 */
const meta = {
  title: "Common/SortableHeader",
  component: SortableHeader,
  args: {
    column: "name",
    sorting: { ordering: "", sortFields: ["name"], onSort: fn() },
    children: "Name",
  },
  decorators: [
    (Story) => (
      <table className="table">
        <thead>
          <tr>
            <Story />
          </tr>
        </thead>
      </table>
    ),
  ],
} satisfies Meta<typeof SortableHeader>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Unsorted: Story = {};

export const Ascending: Story = {
  args: { sorting: { ordering: "name", sortFields: ["name"], onSort: fn() } },
};

export const Descending: Story = {
  args: { sorting: { ordering: "-name", sortFields: ["name"], onSort: fn() } },
};

/** A column that the list api can't sort by is a plain header. */
export const NotSortable: Story = {
  args: { sorting: { ordering: "", sortFields: [], onSort: fn() } },
};
