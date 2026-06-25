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
 * - vectorstores (Vectorestore[]): Array of vectorstore objects to display.
 * - renderDetailRow (function): Function to render detail rows for vectorstore attributes.
 *
 * Usage:
 * <CardView sessionContext={sessionContext} title="Your Vectorestores" objects={vectorstores} renderDetailRow={renderDetailRow} />
 *
 * This component is intended for use in views where objects are presented in a card/grid format.
 */
import type { VectorestoreCardViewProps } from "@/lib/Types";
import { loggerPrefix } from "@/lib/const";
import { Toolbar } from "@/components/Toolbar";
import { StatusBar } from "@/components/StatusBar";
import { renderDetailRow } from "@/components/CardView/renderDetail";

import "./styles.css";

function CardView({ sessionContext, objects, onRequery }: VectorestoreCardViewProps) {
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
                    {renderDetailRow("ID", vectorstore.id, "number")}
                    {renderDetailRow("Manifest URL", vectorstore.manifestUrl, "url")}
                    {renderDetailRow("Owner", vectorstore.userProfile?.user?.username)}
                    {renderDetailRow("Owner Email", vectorstore.userProfile?.user?.email)}
                    {renderDetailRow("Account Number", vectorstore.userProfile?.account?.accountNumber)}
                    {renderDetailRow("Created", vectorstore.createdAt, "dateTime")}
                    {renderDetailRow("Last Updated", vectorstore.updatedAt, "dateTime")}
                    {renderDetailRow("Version", vectorstore.version)}
                    {renderDetailRow("Description", vectorstore.description)}
                    {renderDetailRow("Tags", vectorstore.tags, "str[]")}
                    {renderDetailRow("Annotations", vectorstore.annotations, "json")}
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
