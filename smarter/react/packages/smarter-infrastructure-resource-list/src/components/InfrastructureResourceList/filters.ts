/** Filtering and pagination of the infrastructure resource list, which the Django api applies. */
export type StatusFilter = "active" | "destroyed" | "all";

export type Filters = {
  status: StatusFilter;
  billableOnly: boolean;
  provider: string;
  resourceType: string;
  text: string;
};

export const defaultFilters: Filters = {
  status: "active",
  billableOnly: false,
  provider: "",
  resourceType: "",
  text: "",
};

export const pageSizes = [25, 50, 100, 250];
export const defaultPageSize = 50;

/** How long to wait after the last keystroke of a search before it is requested, in milliseconds. */
export const searchDelay = 300;

/** The list api's request body, for a page of the resources that match the filters. */
export function listRequest(filters: Filters, page: number, pageSize: number): string {
  return JSON.stringify({ ...filters, text: filters.text.trim(), page, pageSize });
}
