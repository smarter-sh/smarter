/**
 * DetailView React Component
 *
 * The Details tab of a connection's detail, which the list opens when one of its rows is chosen (see
 * TabbedListView and ResourceDetail in @smarter/common): the connection's description and actions, then what kind
 * of connection it is, and the metadata that every resource has. Its host, credentials and proxy are in its
 * manifest, on the detail's Manifest tab; the passwords and keys that it uses are Secrets, whose values are never
 * shown.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for the actions.
 * - object (Connection): The connection.
 * - onRequery (function): Reloads the list, after an action changes it.
 * - filtering (Filtering): Narrows the list by a tag or annotation that is clicked.
 *
 * Usage:
 * <DetailView sessionContext={sessionContext} object={connection} onRequery={onRequery} filtering={filtering} />
 */
import { DetailField, DetailOverview, DetailSection, gettext, ResourceMetadataSection } from "@smarter/common";

import type { ConnectionDetailViewProps, ConnectionKind } from "@/lib/Types";
import { Toolbar } from "@/components/Toolbar";

/** What a kind of connection connects to, in the language of the page. A kind that this app doesn't know is shown as it is. */
function kindLabel(kind: ConnectionKind | string | null | undefined): string | null {
  switch (kind) {
    case "SqlConnection":
      return gettext("SQL database");
    case "ApiConnection":
      return gettext("REST API");
    default:
      return kind || null;
  }
}

function DetailView({ sessionContext, object: connection, onRequery, filtering }: ConnectionDetailViewProps) {
  const label = kindLabel(connection.kind);
  return (
    <>
      <DetailOverview description={connection.description}>
        <span className={`badge ${connection.ready ? "badge-light-success" : "badge-light"} fw-semibold`}>
          {connection.ready ? gettext("Ready") : gettext("Not ready")}
        </span>
        {label && <span className="badge badge-light-primary fw-semibold">{label}</span>}
        <Toolbar sessionContext={sessionContext} connection={connection} onRequery={onRequery} />
      </DetailOverview>

      <DetailSection title={gettext("Connection")} icon="data">
        <DetailField
          label={gettext("Kind")}
          value={connection.kind}
          type="code"
          help={gettext(
            "A SqlConnection connects a plugin to a SQL database; an ApiConnection connects it to a REST API.",
          )}
        />
        <DetailField label={gettext("Connects to")} value={label} />
        <DetailField
          label={gettext("Ready")}
          value={connection.ready}
          type="bool"
          help={gettext("Whether the plugins that use the connection can use it.")}
        />
        <DetailField
          label={gettext("Credentials")}
          help={gettext(
            "The host, credentials and proxy are in the connection's manifest. Passwords and keys are Secrets, referred to by name.",
          )}
        >
          <span className="text-gray-600 fst-italic">
            <i className="ki-outline ki-lock fs-7 me-1" aria-hidden="true" />
            {gettext("Kept in Secrets, and never shown")}
          </span>
        </DetailField>
      </DetailSection>

      <ResourceMetadataSection resource={connection} filtering={filtering} />
    </>
  );
}

export default DetailView;
