/**
 * CardView React Component
 *
 * This component renders vectorstore resources as individual cards, displaying detailed information and actions for each vectorstore.
 * It is used to present vectorstores in a card-based layout, with modals for clone, rename, and delete actions.
 *
 * Features:
 * - Displays vectorstore details in a visually distinct card format.
 * - Integrates action buttons for open, edit, clone, rename, and delete operations.
 * - Uses modal dialogs for clone, rename, and delete workflows (scaffolded for further logic).
 * - Supports a custom detail row renderer for flexible display of vectorstore attributes.
 * - Accepts a custom CSS class for layout control.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for actions.
 * - title (string): Title displayed above the card list.
 * - vectorstores (Vectorstore[]): Array of vectorstore objects to display.
 * - renderDetailRow (function): Function to render detail rows for vectorstore attributes.
 *
 * Usage:
 * <CardView sessionContext={sessionContext} title="Your Vectorstores" objects={vectorstores} renderDetailRow={renderDetailRow} />
 *
 * This component is intended for use in views where objects are presented in a card/grid format.
 */
import type { VectorstoreCardViewProps } from "@/lib/Types";
import { loggerPrefix } from "@/lib/const";
import { Toolbar } from "@/components/Toolbar";
import { StatusBar } from "@/components/StatusBar";
import { renderDetailRow } from "@/components/CardView/renderDetail";
import { databaseLabel, formatCount } from "@/lib/format";

import "@/components/CardView/styles.css";
import { gettext } from "@smarter/common";

function CardView({ sessionContext, objects, onRequery }: VectorstoreCardViewProps) {
  console.debug(loggerPrefix, "Rendering CardView with objects:", objects, sessionContext);

  return (
    <div className="row g-4 p-4">
      {Array.isArray(objects) &&
        objects.map((vectorstore) => (
          <div className="col-12" key={vectorstore.id}>
            <div className="card h-100">
              <div className="card-header d-flex justify-content-between align-items-center bg-white border-bottom-0 pb-0">
                <Toolbar sessionContext={sessionContext} vectorstore={vectorstore} onRequery={onRequery} />
                <span className="border rounded p-2">
                  <StatusBar vectorstore={vectorstore} />
                </span>
              </div>
              <div className="card-body">
                <h5 className="card-title mb-3 text-primary fw-bold text-center">
                  <a href={vectorstore.manifestUrl} className="text-decoration-none text-primary">
                    {vectorstore.name}
                  </a>
                </h5>
                <table className="table table-bordered table-sm align-middle mb-0">
                  <tbody>
                    {renderDetailRow(gettext("ID"), vectorstore.id, "number")}
                    {renderDetailRow(gettext("Manifest URL"), vectorstore.manifestUrl, "url")}
                    {renderDetailRow(gettext("Description"), vectorstore.description)}
                    {renderDetailRow(gettext("Database"), databaseLabel(vectorstore))}
                    {renderDetailRow(gettext("Status"), vectorstore.status)}
                    {renderDetailRow(gettext("Status Message"), vectorstore.statusMessage)}
                    {renderDetailRow(gettext("Active"), vectorstore.isActive, "bool")}
                    {renderDetailRow(gettext("Index or Collection"), vectorstore.indexName)}
                    {renderDetailRow(gettext("Endpoint"), vectorstore.endpointUrl)}
                    {renderDetailRow(gettext("ApiConnection"), vectorstore.connection)}
                    {renderDetailRow(gettext("API Key Secret"), vectorstore.apiKeySecret)}
                    {renderDetailRow(
                      gettext("Embeddings"),
                      vectorstore.embeddingsProvider
                        ? `${vectorstore.embeddingsProvider} / ${vectorstore.embeddingsModel}`
                        : vectorstore.embeddingsModel,
                    )}
                    {renderDetailRow(gettext("Dimensions"), vectorstore.dimension, "number")}
                    {renderDetailRow(gettext("Metric"), vectorstore.metric)}
                    {renderDetailRow(gettext("Deletion Protection"), vectorstore.deletionProtection, "bool")}
                    {renderDetailRow(gettext("Vectors"), formatCount(vectorstore.vectorCount))}
                    {renderDetailRow(gettext("Documents"), formatCount(vectorstore.documentCount))}
                    {renderDetailRow(gettext("Snapshots"), formatCount(vectorstore.snapshotCount))}
                    {renderDetailRow(gettext("Deployed"), vectorstore.deployedAt, "dateTime")}
                    {renderDetailRow(gettext("Last Checked"), vectorstore.lastCheckedAt, "dateTime")}
                    {renderDetailRow(gettext("Last Snapshot"), vectorstore.lastSnapshotAt, "dateTime")}
                    {renderDetailRow(gettext("Owner"), vectorstore.userProfile?.user?.username)}
                    {renderDetailRow(gettext("Account Number"), vectorstore.userProfile?.account?.accountNumber)}
                    {renderDetailRow(gettext("Created"), vectorstore.createdAt, "dateTime")}
                    {renderDetailRow(gettext("Last Updated"), vectorstore.updatedAt, "dateTime")}
                    {renderDetailRow(gettext("Version"), vectorstore.version)}
                    {renderDetailRow(gettext("Tags"), vectorstore.tags, "str[]")}
                    {renderDetailRow(gettext("Annotations"), vectorstore.annotations, "json")}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        ))}
    </div>
  );
}

export default CardView;
