/**
 * InfrastructureResourceList
 *
 * Lists the ledger of the cloud resources that the platform has created: a summary of all of
 * them, and the most recent, which can be filtered by status, by whether they are billable, by
 * provider, and by text. The ledger is written by the platform, so the list is read-only.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { Loading, fetchDjangoUrl, formatDateTime } from "@smarter/common";
import type { SessionContext } from "@smarter/common";

import type {
  InfrastructureResource,
  InfrastructureResourceListResponse,
  InfrastructureResourceSummary,
} from "@/lib/Types";
import { loggerPrefix } from "@/lib/const";

import { defaultFilters, filterResources } from "./filters";
import type { Filters, StatusFilter } from "./filters";

import "./styles.css";

function SummaryTile({ label, value, className }: { label: string; value: number; className?: string }) {
  return (
    <div className="col-6 col-md-3">
      <div
        className={`infrastructure-summary-tile border rounded p-4 ${className ?? ""}`}
        aria-label={`${label}: ${value}`}
      >
        <div className="fs-2 fw-bold">{value.toLocaleString()}</div>
        <div className="text-muted fs-7">{label}</div>
      </div>
    </div>
  );
}

function Summary({ summary }: { summary: InfrastructureResourceSummary }) {
  return (
    <div className="row g-3 mb-5" aria-label="Summary">
      <SummaryTile label="Active" value={summary.active} />
      <SummaryTile
        label="Active and billable"
        value={summary.activeBillable}
        className={summary.activeBillable > 0 ? "infrastructure-summary-billable" : ""}
      />
      <SummaryTile label="Destroyed" value={summary.destroyed} />
      <SummaryTile label="Total" value={summary.total} />
    </div>
  );
}

function ResourceRow({ resource }: { resource: InfrastructureResource }) {
  return (
    <tr>
      <td>
        <span className="fw-semibold">{resource.resourceName}</span>
        {resource.resourceId && <div className="text-muted fs-8 text-break">{resource.resourceId}</div>}
      </td>
      <td>
        <code>{resource.resourceType}</code>
      </td>
      <td>
        {resource.provider} / {resource.service}
      </td>
      <td>
        {resource.billable ? (
          <span className="badge badge-light-warning">Billable</span>
        ) : (
          <span className="text-muted">No</span>
        )}
      </td>
      <td>
        {resource.status === "active" ? (
          <span className="badge badge-light-success">Active</span>
        ) : (
          <span className="badge badge-light" title={resource.destroyedAt ?? ""}>
            Destroyed
          </span>
        )}
      </td>
      <td className="d-none d-lg-table-cell" title={resource.createdAt}>
        {formatDateTime(resource.createdAt)}
      </td>
    </tr>
  );
}

export default function InfrastructureResourceList({ sessionContext }: { sessionContext: SessionContext }) {
  const [data, setData] = useState<InfrastructureResourceListResponse | null>(null);
  const [errMessage, setErrMessage] = useState("");
  const [filters, setFilters] = useState<Filters>(defaultFilters);

  const load = useCallback(() => {
    fetchDjangoUrl(sessionContext, sessionContext.ApiUrl, JSON.stringify({}))
      .then(async (response) => {
        if (!response.ok) {
          const body = await response.json().catch(() => null);
          throw new Error(body?.error || `Failed to load the infrastructure resources (${response.status}).`);
        }
        setData((await response.json()) as InfrastructureResourceListResponse);
        setErrMessage("");
      })
      .catch((error: Error) => {
        console.error(loggerPrefix, "Error loading infrastructure resources:", error);
        setErrMessage(error.message);
      });
  }, [sessionContext]);

  useEffect(() => {
    load();
  }, [load]);

  const providers = useMemo(
    () => Array.from(new Set((data?.objects ?? []).map((resource) => resource.provider))).sort(),
    [data],
  );
  const resources = useMemo(() => filterResources(data?.objects ?? [], filters), [data, filters]);
  const setFilter = <K extends keyof Filters>(key: K, value: Filters[K]) => setFilters({ ...filters, [key]: value });

  return (
    <div className="card mt-5">
      <div className="card-body">
        {errMessage && (
          <div className="alert alert-danger" role="alert">
            {errMessage}
          </div>
        )}
        {data === null && !errMessage && <Loading />}
        {data && (
          <>
            <Summary summary={data.summary} />
            <div className="d-flex flex-wrap gap-3 align-items-center mb-4">
              <select
                className="form-select form-select-sm w-auto"
                aria-label="Status"
                value={filters.status}
                onChange={(event) => setFilter("status", event.target.value as StatusFilter)}
              >
                <option value="active">Active</option>
                <option value="destroyed">Destroyed</option>
                <option value="all">All</option>
              </select>
              <select
                className="form-select form-select-sm w-auto"
                aria-label="Provider"
                value={filters.provider}
                onChange={(event) => setFilter("provider", event.target.value)}
              >
                <option value="">All providers</option>
                {providers.map((provider) => (
                  <option key={provider} value={provider}>
                    {provider}
                  </option>
                ))}
              </select>
              <div className="form-check form-check-sm">
                <input
                  className="form-check-input"
                  type="checkbox"
                  id="infrastructure-billable-only"
                  checked={filters.billableOnly}
                  onChange={(event) => setFilter("billableOnly", event.target.checked)}
                />
                <label className="form-check-label" htmlFor="infrastructure-billable-only">
                  Billable only
                </label>
              </div>
              <input
                type="search"
                className="form-control form-control-sm w-auto"
                placeholder="Search"
                aria-label="Search"
                value={filters.text}
                onChange={(event) => setFilter("text", event.target.value)}
              />
              <button type="button" className="btn btn-sm btn-light ms-auto" onClick={load}>
                <i className="bi bi-arrow-clockwise" /> Refresh
              </button>
            </div>
            {resources.length === 0 ? (
              <div className="text-muted p-4">
                {data.objects.length === 0
                  ? "The platform has not created any cloud resources yet."
                  : "No resources match the filters."}
              </div>
            ) : (
              <div className="table-responsive">
                <table className="table table-striped table-hover align-middle border">
                  <thead className="table-light">
                    <tr>
                      <th>Resource</th>
                      <th>Type</th>
                      <th>Provider / service</th>
                      <th>Billable</th>
                      <th>Status</th>
                      <th className="d-none d-lg-table-cell">Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {resources.map((resource) => (
                      <ResourceRow key={resource.id} resource={resource} />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {data.objects.length < data.summary.total && (
              <div className="text-muted fs-8">
                Showing the {data.objects.length.toLocaleString()} most recent of {data.summary.total.toLocaleString()}{" "}
                resources.
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
