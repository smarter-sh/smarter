/**
 * CardView React Component
 *
 * This component renders vectorsearch resources as individual cards, displaying detailed information and actions for each vectorsearch.
 * It is used to present vectorsearchs in a card-based layout, with modals for clone, rename, and delete actions.
 *
 * Features:
 * - Displays vectorsearch details in a visually distinct card format.
 * - Integrates action buttons for open, edit, clone, rename, and delete operations.
 * - Uses modal dialogs for clone, rename, and delete workflows (scaffolded for further logic).
 * - Supports a custom detail row renderer for flexible display of vectorsearch attributes.
 * - Accepts a custom CSS class for layout control.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for actions.
 * - title (string): Title displayed above the card list.
 * - vectorsearchs (Vectorsearch[]): Array of vectorsearch objects to display.
 * - renderDetailRow (function): Function to render detail rows for vectorsearch attributes.
 *
 * Usage:
 * <CardView sessionContext={sessionContext} title="Your Vectorsearch" objects={vectorsearchs} renderDetailRow={renderDetailRow} />
 *
 * This component is intended for use in views where objects are presented in a card/grid format.
 */
import type { VectorsearchCardViewProps } from "@/lib/Types";
import { loggerPrefix } from "@/lib/const";
import { Toolbar } from "@/components/Toolbar";
import { StatusBar } from "@/components/StatusBar";
import { renderDetailRow } from "@/components/CardView/renderDetail";

import "./styles.css";

function CardView({ sessionContext, objects, onRequery }: VectorsearchCardViewProps) {
  console.debug(loggerPrefix, "Rendering CardView with objects:", objects, sessionContext);

  return (
    <div className="row g-4 p-4">
      {Array.isArray(objects) &&
        objects.map((vectorsearch) => (
          <div className="col-12" key={vectorsearch.id}>
            <div className="card h-100">
              <div className="card-header d-flex justify-content-between align-items-center bg-white border-bottom-0 pb-0">
                <Toolbar sessionContext={sessionContext} vectorsearch={vectorsearch} onRequery={onRequery} />
                <span className="border rounded p-2">
                  <StatusBar vectorsearch={vectorsearch} />
                </span>
              </div>
              <div className="card-body">
                <h5 className="card-title mb-3 text-primary fw-bold text-center">
                  <a href={vectorsearch.manifestUrl} className="text-decoration-none text-primary">
                    {vectorsearch.name}
                  </a>
                </h5>
                <table className="table table-bordered table-sm align-middle mb-0">
                  <tbody>
                    {renderDetailRow("ID", vectorsearch.id, "number")}
                    {renderDetailRow("Vectorstore", vectorsearch.vectorstore)}
                    {renderDetailRow("Search Type", vectorsearch.searchType)}
                    {renderDetailRow("Manifest URL", vectorsearch.manifestUrl, "url")}
                    {renderDetailRow("Base URL", vectorsearch.baseUrl, "url")}
                    {renderDetailRow("Owner", vectorsearch.userProfile?.user?.username)}
                    {renderDetailRow("Owner Email", vectorsearch.userProfile?.user?.email)}
                    {renderDetailRow("Account Number", vectorsearch.userProfile?.account?.accountNumber)}
                    {renderDetailRow("Created", vectorsearch.createdAt, "dateTime")}
                    {renderDetailRow("Last Updated", vectorsearch.updatedAt, "dateTime")}
                    {renderDetailRow("Version", vectorsearch.version)}
                    {renderDetailRow("Description", vectorsearch.description)}
                    {renderDetailRow("Tags", vectorsearch.tags, "str[]")}
                    {renderDetailRow("Annotations", vectorsearch.annotations, "json")}
                    {renderDetailRow("Ready", vectorsearch.ready, "bool")}
                    {renderDetailRow(
                      "RFC 1034 Compliant Name",
                      vectorsearch.rfc1034CompliantName
                    )}
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
