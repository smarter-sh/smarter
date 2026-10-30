/**
 * DetailView React Component
 *
 * The Details tab of a secret's detail, which the list opens when one of its rows is chosen (see TabbedListView
 * and ResourceDetail in @smarter/common): the secret's description and actions, then how it is stored and used,
 * and the metadata that every resource has. The secret's value is never shown.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for the actions.
 * - object (Secret): The secret.
 * - onRequery (function): Reloads the list, after an action changes it.
 * - filtering (Filtering): Narrows the list by a tag or annotation that is clicked.
 *
 * Usage:
 * <DetailView sessionContext={sessionContext} object={secret} onRequery={onRequery} filtering={filtering} />
 */
import { DetailField, DetailOverview, DetailSection, gettext, ResourceMetadataSection } from "@smarter/common";

import type { SecretDetailViewProps } from "@/lib/Types";
import { Toolbar } from "@/components/Toolbar";

/** Whether a secret's expiration date has passed. A secret without one never expires. */
function isExpired(expiresAt: string | null): boolean {
  return !!expiresAt && new Date(expiresAt).getTime() < Date.now();
}

function DetailView({ sessionContext, object: secret, onRequery, filtering }: SecretDetailViewProps) {
  const expired = isExpired(secret.expiresAt);
  return (
    <>
      <DetailOverview description={secret.description}>
        <span className={`badge ${secret.ready ? "badge-light-success" : "badge-light"} fw-semibold`}>
          {secret.ready ? gettext("Ready") : gettext("Not ready")}
        </span>
        {expired && <span className="badge badge-light-danger fw-semibold">{gettext("Expired")}</span>}
        <Toolbar sessionContext={sessionContext} secret={secret} onRequery={onRequery} />
      </DetailOverview>

      <DetailSection title={gettext("Value and usage")} icon="lock-2">
        <DetailField
          label={gettext("Value")}
          help={gettext(
            "The value is encrypted when it is stored. Resources that use the secret refer to it by name, so the value is never exposed.",
          )}
        >
          <span className="text-gray-600 fst-italic">
            <i className="ki-outline ki-lock fs-7 me-1" aria-hidden="true" />
            {gettext("Encrypted, and never shown")}
          </span>
        </DetailField>
        <DetailField
          label={gettext("Ready")}
          value={secret.ready}
          type="bool"
          help={gettext("Whether the secret can be used by the resources that refer to it.")}
        />
        <DetailField
          label={gettext("Last accessed")}
          value={secret.lastAccessed}
          type="dateTime"
          help={gettext("When a resource last read the secret's value.")}
        />
        <DetailField
          label={gettext("Expires")}
          value={secret.expiresAt}
          type="dateTime"
          help={gettext("When the secret expires. A secret without an expiration date never expires.")}
        />
      </DetailSection>

      <ResourceMetadataSection resource={secret} filtering={filtering} />
    </>
  );
}

export default DetailView;
