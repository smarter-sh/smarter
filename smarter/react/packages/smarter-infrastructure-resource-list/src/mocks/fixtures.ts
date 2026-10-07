/**
 * Example data for this package's stories and tests: what the Django api returns.
 * See smarter.apps.infrastructure.views.listview.InfrastructureResourceListApiView.
 */
import type { SessionContext } from "@smarter/common";

import type { InfrastructureResource, InfrastructureResourceListResponse } from "@/lib/Types";

export const API_URL = "/infrastructure/react-integration/api/listview/";

export const sessionContext: SessionContext = {
  ApiUrl: API_URL,
  csrfCookieName: "csrftoken",
  djangoSessionCookieName: "sessionid",
  cookieDomain: "localhost",
  debugMode: false,
  smarterClient: "@smarter/infrastructure-resource-list",
  smarterClientVersion: "0.0.0",
  smarterRequestId: "storybook-request-id",
};

export function makeResource(overrides: Partial<InfrastructureResource> = {}): InfrastructureResource {
  return {
    id: 1,
    createdAt: "2026-10-01T12:00:00Z",
    updatedAt: "2026-10-01T12:00:00Z",
    provider: "aws",
    service: "dns",
    resourceType: "dns.zone",
    resourceName: "customer.example.com",
    resourceId: "Z148QEXAMPLE8V",
    billable: true,
    status: "active",
    destroyedAt: null,
    ...overrides,
  };
}

export const resources: InfrastructureResource[] = [
  makeResource(),
  makeResource({
    id: 2,
    service: "dns",
    resourceType: "dns.record",
    resourceName: "example.3141-5926-5359.api.example.com A",
    billable: false,
  }),
  makeResource({
    id: 3,
    service: "certificates",
    resourceType: "certificate",
    resourceName: "customer.example.com",
    resourceId: "arn:aws:acm:us-east-1:123456789012:certificate/abcd",
    billable: false,
  }),
  makeResource({
    id: 4,
    service: "kubernetes",
    resourceType: "kubernetes.persistentvolumeclaim",
    resourceName: "smarter.sh/vectorstore=qdrant-1",
    resourceId: "smarter.sh/vectorstore=qdrant-1",
    status: "destroyed",
    destroyedAt: "2026-10-03T08:00:00Z",
  }),
  makeResource({ id: 5, provider: "memory", resourceName: "local.example.com", resourceId: "Z000000000001" }),
];

export const listResponse: InfrastructureResourceListResponse = {
  summary: { total: 5, active: 4, activeBillable: 2, destroyed: 1 },
  objects: resources,
};
