/**
 * Central type definitions for the Infrastructure Resource List React application.
 *
 * The objects come from smarter.apps.infrastructure.views.listview.InfrastructureResourceListApiView,
 * serialized by smarter.apps.infrastructure.serializers.InfrastructureResourceSerializer.
 */

export type InfrastructureResourceStatus = "active" | "destroyed";

/** A cloud resource that the platform created, and whether it still exists. */
export type InfrastructureResource = {
  id: number;
  createdAt: string;
  updatedAt: string;
  /** The cloud provider, e.g. aws. */
  provider: string;
  /** The infrastructure service, e.g. dns. */
  service: string;
  /** The kind of resource, e.g. dns.zone. */
  resourceType: string;
  /** The resource's name, e.g. example.com. */
  resourceName: string;
  /** The provider's id of the resource, if any. */
  resourceId: string;
  billable: boolean;
  status: InfrastructureResourceStatus;
  destroyedAt: string | null;
};

/** Counts of all of the ledger's resources, not only those that the list returns. */
export type InfrastructureResourceSummary = {
  total: number;
  active: number;
  activeBillable: number;
  destroyed: number;
};

export type InfrastructureResourceListResponse = {
  summary: InfrastructureResourceSummary;
  objects: InfrastructureResource[];
};
