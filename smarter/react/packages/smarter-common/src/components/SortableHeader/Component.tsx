/**
 * SortableHeader React Component
 *
 * A column header of a list view's table, which sorts the list by its column when it is clicked.
 *
 * The list is paginated, so its rows are not sorted in the browser: the page shown holds only some
 * of the objects. Instead, the header asks its TabbedListView, through sorting.onSort, for another
 * ordering, and the TabbedListView requests the first page of the objects in that order from its
 * list api, which sorts all of them.
 *
 * Each click moves the column to its next order: ascending, then descending, then back to the list
 * api's default order. A sorted column shows an arrow, and its aria-sort says which way it is
 * sorted.
 *
 * Props:
 * - column (string): The column's name in the list api, e.g. "name" or "updatedAt".
 * - sorting (Sorting, optional): The list's sort. Without it, or when the list api can't sort by
 *   the column, the header is a plain, unsortable header.
 * - className (string, optional): The header cell's classes, e.g. for responsive visibility.
 * - children: The header's title.
 *
 * Usage:
 * <SortableHeader column="name" sorting={sorting} className="p-1">Name</SortableHeader>
 */
import type { ReactNode } from "react";

import type { Sorting } from "../../lib/Types";

type SortableHeaderProps = {
  column: string;
  sorting?: Sorting;
  className?: string;
  children: ReactNode;
};

/** The ordering that a click on a column's header requests: ascending, then descending, then the default order. */
export function nextOrdering(column: string, ordering: string): string {
  if (ordering === column) return `-${column}`;
  if (ordering === `-${column}`) return "";
  return column;
}

export default function SortableHeader({ column, sorting, className, children }: SortableHeaderProps) {
  if (!sorting || !sorting.sortFields.includes(column)) {
    return <th className={className}>{children}</th>;
  }
  const direction =
    sorting.ordering === column ? "ascending" : sorting.ordering === `-${column}` ? "descending" : "none";
  const icon = { ascending: "fa-sort-up", descending: "fa-sort-down", none: "fa-sort opacity-25" }[direction];
  return (
    <th className={className} aria-sort={direction}>
      <button
        type="button"
        className="btn btn-link p-0 border-0 align-baseline text-reset text-decoration-none text-nowrap"
        style={{ font: "inherit" }}
        onClick={() => sorting.onSort(nextOrdering(column, sorting.ordering))}
      >
        {children}
        <i className={`fas ${icon} ms-1`} aria-hidden="true" />
      </button>
    </th>
  );
}
