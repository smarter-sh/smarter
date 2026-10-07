/** Filtering of the infrastructure resource list. */
import type { InfrastructureResource } from "@/lib/Types";

export type StatusFilter = "active" | "destroyed" | "all";

export type Filters = {
  status: StatusFilter;
  billableOnly: boolean;
  provider: string;
  text: string;
};

export const defaultFilters: Filters = { status: "active", billableOnly: false, provider: "", text: "" };

/** The resources that match the filters. */
export function filterResources(resources: InfrastructureResource[], filters: Filters): InfrastructureResource[] {
  const text = filters.text.trim().toLowerCase();
  return resources.filter(
    (resource) =>
      (filters.status === "all" || resource.status === filters.status) &&
      (!filters.billableOnly || resource.billable) &&
      (!filters.provider || resource.provider === filters.provider) &&
      (!text ||
        [resource.resourceName, resource.resourceType, resource.resourceId, resource.service].some((value) =>
          value.toLowerCase().includes(text),
        )),
  );
}
