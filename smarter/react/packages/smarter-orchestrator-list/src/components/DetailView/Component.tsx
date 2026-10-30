/**
 * DetailView React Component
 *
 * The Details tab of an orchestrator's detail, which the list opens when one of its rows is chosen (see
 * TabbedListView and ResourceDetail in @smarter/common): the orchestrator's description, status and actions, then how
 * it coordinates its LLMClients, the LLMClients themselves (its harnesses), and the metadata that every resource has.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for the actions.
 * - object (Orchestrator): The orchestrator.
 * - onRequery (function): Reloads the list, after an action changes it.
 * - filtering (Filtering): Narrows the list by a tag or annotation that is clicked.
 *
 * Usage:
 * <DetailView sessionContext={sessionContext} object={orchestrator} onRequery={onRequery} filtering={filtering} />
 */
import {
  DetailField,
  DetailOverview,
  DetailSection,
  DetailValue,
  gettext,
  ResourceMetadataSection,
} from "@smarter/common";

import type { OrchestratorDetailViewProps, OrchestratorHarness } from "@/lib/Types";
import { Toolbar } from "@/components/Toolbar";

/** The orchestrator's harnesses, in the order in which they run. */
function HarnessTable({ harnesses }: { harnesses: OrchestratorHarness[] }) {
  const ordered = [...harnesses].sort((a, b) => a.executionOrder - b.executionOrder);
  return (
    <div className="table-responsive">
      <table className="table table-sm table-row-bordered align-middle mb-0">
        <thead>
          <tr className="fw-semibold text-gray-600">
            <th scope="col">{gettext("Order")}</th>
            <th scope="col">{gettext("LLMClient")}</th>
            <th scope="col">{gettext("Role")}</th>
            <th scope="col">{gettext("Active")}</th>
            <th scope="col">{gettext("Overrides")}</th>
          </tr>
        </thead>
        <tbody>
          {ordered.map((harness) => (
            <tr key={`${harness.executionOrder}-${harness.llmClientName}`}>
              <td>
                <DetailValue value={harness.executionOrder} type="number" />
              </td>
              <td>
                <DetailValue value={harness.llmClientName} type="code" />
              </td>
              <td>{harness.role}</td>
              <td>
                <DetailValue value={harness.isActive} type="bool" />
              </td>
              <td>
                <DetailValue
                  value={harness.config && Object.keys(harness.config).length ? harness.config : null}
                  type="json"
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DetailView({ sessionContext, object: orchestrator, onRequery, filtering }: OrchestratorDetailViewProps) {
  const harnesses = orchestrator.harnesses ?? [];
  return (
    <>
      <DetailOverview description={orchestrator.description}>
        <span className={`badge ${orchestrator.isActive ? "badge-light-success" : "badge-light"} fw-semibold`}>
          {orchestrator.isActive ? gettext("Active") : gettext("Inactive")}
        </span>
        <Toolbar sessionContext={sessionContext} orchestrator={orchestrator} onRequery={onRequery} />
      </DetailOverview>

      <DetailSection title={gettext("Orchestration")} icon="abstract-26">
        <DetailField
          label={gettext("Strategy")}
          value={orchestrator.strategy}
          help={gettext(
            "How the orchestrator coordinates its LLMClients: in sequence, in parallel, under a supervisor, through a router, by voting, or by debate.",
          )}
        />
        <DetailField
          label={gettext("Maximum iterations")}
          value={orchestrator.maxIterations}
          type="number"
          help={gettext("The most times that the orchestration loop may run: a guard against runaway loops.")}
        />
      </DetailSection>

      <DetailSection title={gettext("Harnesses")} icon="people">
        <DetailField
          label={gettext("LLMClients")}
          wide
          help={gettext(
            "The LLMClients that the orchestrator coordinates, each with its role. The order applies to the sequential and supervisor strategies, and each may override its LLMClient's settings.",
          )}
        >
          {harnesses.length ? <HarnessTable harnesses={harnesses} /> : <DetailValue value={null} />}
        </DetailField>
      </DetailSection>

      <ResourceMetadataSection resource={orchestrator} filtering={filtering}>
        <DetailField
          label={gettext("Ready")}
          value={orchestrator.ready}
          type="bool"
          help={gettext("Whether the orchestrator is ready to serve requests.")}
        />
        <DetailField label={gettext("RFC 1034 compliant name")} value={orchestrator.rfc1034CompliantName} type="code" />
      </ResourceMetadataSection>
    </>
  );
}

export default DetailView;
