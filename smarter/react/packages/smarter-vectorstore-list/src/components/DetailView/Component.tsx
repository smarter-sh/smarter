/**
 * DetailView React Component
 *
 * The Details tab of a vectorstore's detail, which the list opens when one of its rows is chosen (see
 * TabbedListView and ResourceDetail in @smarter/common): the vectorstore's description, status and actions, then
 * its database, how its documents are embedded, what it holds, its lifecycle, and the metadata that every resource
 * has.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for the actions.
 * - object (Vectorstore): The vectorstore.
 * - onRequery (function): Reloads the list, after an action changes it.
 * - filtering (Filtering): Narrows the list by a tag or annotation that is clicked.
 *
 * Usage:
 * <DetailView sessionContext={sessionContext} object={vectorstore} onRequery={onRequery} filtering={filtering} />
 */
import {
  DetailField,
  DetailOverview,
  DetailSection,
  DetailValue,
  gettext,
  ResourceMetadataSection,
} from "@smarter/common";

import type { VectorstoreDetailViewProps } from "@/lib/Types";
import { BACKEND_LABELS, HOSTING_LABELS, STATUS_BADGES } from "@/lib/format";
import { StatusBar } from "@/components/StatusBar";
import { Toolbar } from "@/components/Toolbar";

function DetailView({ sessionContext, object: vectorstore, onRequery, filtering }: VectorstoreDetailViewProps) {
  const status = STATUS_BADGES[vectorstore.status];
  return (
    <>
      <DetailOverview description={vectorstore.description}>
        <StatusBar vectorstore={vectorstore} />
        <Toolbar sessionContext={sessionContext} vectorstore={vectorstore} onRequery={onRequery} />
      </DetailOverview>

      <DetailSection title={gettext("Database")} icon="data">
        <DetailField label={gettext("Backend")} value={BACKEND_LABELS[vectorstore.backend] ?? vectorstore.backend} />
        <DetailField
          label={gettext("Hosting")}
          value={HOSTING_LABELS[vectorstore.hosting] ?? vectorstore.hosting}
          help={gettext("Self-hosted: Smarter runs its database. Managed: the backend's cloud service runs it.")}
        />
        <DetailField label={gettext("Index or collection")} value={vectorstore.indexName} type="code" />
        <DetailField label={gettext("Endpoint")} value={vectorstore.endpointUrl} type="code" />
        <DetailField
          label={gettext("ApiConnection")}
          value={vectorstore.connection}
          help={gettext("The ApiConnection that connects to a managed database.")}
        />
        <DetailField
          label={gettext("API key secret")}
          value={vectorstore.apiKeySecret}
          help={gettext("The Smarter Secret that holds the database's API key. The key itself is never shown.")}
        />
        <DetailField label={gettext("Active")} value={vectorstore.isActive} type="bool" />
        <DetailField
          label={gettext("Deletion protection")}
          value={vectorstore.deletionProtection}
          type="bool"
          help={gettext("Whether its database, and its data, are kept when it is deleted or undeployed.")}
        />
      </DetailSection>

      <DetailSection title={gettext("Embeddings")} icon="abstract-26">
        <DetailField
          label={gettext("Provider")}
          value={vectorstore.embeddingsProvider}
          help={gettext("The Provider whose model turns documents and queries into vectors.")}
        />
        <DetailField label={gettext("Model")} value={vectorstore.embeddingsModel} type="code" />
        <DetailField
          label={gettext("Dimensions")}
          value={vectorstore.dimension}
          type="number"
          help={gettext("The length of each vector. It must match the embeddings model's.")}
        />
        <DetailField
          label={gettext("Metric")}
          value={vectorstore.metric}
          help={gettext("How the similarity of two vectors is measured.")}
        />
      </DetailSection>

      <DetailSection title={gettext("Contents")} icon="document">
        <DetailField label={gettext("Vectors")} value={vectorstore.vectorCount ?? 0} type="number" />
        <DetailField label={gettext("Documents")} value={vectorstore.documentCount ?? 0} type="number" />
        <DetailField label={gettext("Snapshots")} value={vectorstore.snapshotCount ?? 0} type="number" />
        <DetailField label={gettext("Statistics")} wide>
          {vectorstore.stats && Object.keys(vectorstore.stats).length ? (
            <DetailValue value={vectorstore.stats} type="json" />
          ) : (
            <DetailValue value={null} />
          )}
        </DetailField>
      </DetailSection>

      <DetailSection title={gettext("Lifecycle")} icon="time">
        <DetailField label={gettext("Status")} value={status?.label ?? vectorstore.status} help={status?.help} />
        <DetailField label={gettext("Deployed")} value={vectorstore.deployedAt} type="dateTime" />
        <DetailField label={gettext("Last checked")} value={vectorstore.lastCheckedAt} type="dateTime" />
        <DetailField label={gettext("Last snapshot")} value={vectorstore.lastSnapshotAt} type="dateTime" />
        <DetailField label={gettext("Last maintenance")} value={vectorstore.lastMaintenanceAt} type="dateTime" />
        <DetailField label={gettext("Status message")} value={vectorstore.statusMessage} wide />
      </DetailSection>

      <ResourceMetadataSection resource={vectorstore} filtering={filtering} />
    </>
  );
}

export default DetailView;
