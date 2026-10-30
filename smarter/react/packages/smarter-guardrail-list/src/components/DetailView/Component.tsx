/**
 * DetailView React Component
 *
 * The Details tab of a guardrail's detail, which the list opens when one of its rows is chosen (see
 * TabbedListView and ResourceDetail in @smarter/common): the guardrail's description and actions, then what it
 * checks, how it detects a problem, what it does about one, and the metadata that every resource has.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for the actions.
 * - object (Guardrail): The guardrail.
 * - onRequery (function): Reloads the list, after an action changes it.
 * - filtering (Filtering): Narrows the list by a tag or annotation that is clicked.
 *
 * Usage:
 * <DetailView sessionContext={sessionContext} object={guardrail} onRequery={onRequery} filtering={filtering} />
 */
import {
  DetailField,
  DetailOverview,
  DetailSection,
  DetailValue,
  gettext,
  ResourceMetadataSection,
} from "@smarter/common";

import type { GuardrailDetailViewProps } from "@/lib/Types";
import { Toolbar } from "@/components/Toolbar";

function DetailView({ sessionContext, object: guardrail, onRequery, filtering }: GuardrailDetailViewProps) {
  return (
    <>
      <DetailOverview description={guardrail.description}>
        <span className={`badge ${guardrail.isActive ? "badge-light-success" : "badge-light"} fw-semibold`}>
          {guardrail.isActive ? gettext("Active") : gettext("Inactive")}
        </span>
        <span className={`badge ${guardrail.mode === "enforce" ? "badge-light-primary" : "badge-light-warning"}`}>
          {guardrail.mode === "enforce" ? gettext("Enforced") : gettext("Monitor only")}
        </span>
        <Toolbar sessionContext={sessionContext} guardrail={guardrail} onRequery={onRequery} />
      </DetailOverview>

      <DetailSection title={gettext("Classification")} icon="category">
        <DetailField
          label={gettext("Stage")}
          value={guardrail.stage}
          help={gettext("Whether it checks the user's prompt (input), the LLM's reply (output), or both.")}
        />
        <DetailField label={gettext("Category")} value={guardrail.category} />
        <DetailField
          label={gettext("Priority")}
          value={guardrail.priority}
          type="number"
          help={gettext("Guardrails with a lower priority run first.")}
        />
        <DetailField label={gettext("Severity")} value={guardrail.severity} type="number" />
        <DetailField label={gettext("Ready")} value={guardrail.ready} type="bool" />
        <DetailField
          label={gettext("Fails closed")}
          value={guardrail.failClosed}
          type="bool"
          help={gettext(
            "Whether a failure of the guardrail itself blocks the request, rather than letting it through.",
          )}
        />
      </DetailSection>

      <DetailSection title={gettext("Detection")} icon="scan-barcode">
        <DetailField label={gettext("Strategy")} value={guardrail.strategy} />
        <DetailField label={gettext("Threshold")} value={guardrail.threshold} type="number" />
        <DetailField label={gettext("Pattern")} value={guardrail.pattern} type="source" wide />
        <DetailField label={gettext("Configuration")} wide>
          {guardrail.config && Object.keys(guardrail.config).length ? (
            <DetailValue value={guardrail.config} type="json" />
          ) : (
            <DetailValue value={null} />
          )}
        </DetailField>
      </DetailSection>

      <DetailSection title={gettext("Response")} icon="message-text-2">
        <DetailField label={gettext("Action")} value={guardrail.action} />
        <DetailField label={gettext("Replacement")} value={guardrail.replacement} type="code" />
        <DetailField
          label={gettext("Message")}
          value={guardrail.message}
          wide
          help={gettext("What the user is told when the guardrail blocks their prompt or the LLM's reply.")}
        />
      </DetailSection>

      <ResourceMetadataSection resource={guardrail} filtering={filtering}>
        <DetailField label={gettext("RFC 1034 compliant name")} value={guardrail.rfc1034CompliantName} type="code" />
      </ResourceMetadataSection>
    </>
  );
}

export default DetailView;
