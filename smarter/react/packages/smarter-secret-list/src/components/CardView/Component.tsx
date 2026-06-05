/**
 * CardView React Component
 *
 * This component renders secret resources as individual cards, displaying detailed information and actions for each secret.
 * It is used to present secrets in a card-based layout, with modals for clone, rename, and delete actions.
 *
 * Features:
 * - Displays secret details in a visually distinct card format.
 * - Integrates action buttons for open, edit, clone, rename, and delete operations.
 * - Uses modal dialogs for clone, rename, and delete workflows (scaffolded for further logic).
 * - Supports a custom detail row renderer for flexible display of secret attributes.
 * - Accepts a custom CSS class for layout control.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for actions.
 * - title (string): Title displayed above the card list.
 * - secrets (Secret[]): Array of secret objects to display.
 * - renderDetailRow (function): Function to render detail rows for secret attributes.
 *
 * Usage:
 * <CardView sessionContext={sessionContext} title="Your Secrets" objects={secrets} renderDetailRow={renderDetailRow} />
 *
 * This component is intended for use in views where objects are presented in a card/grid format.
 */
import type { SecretCardViewProps } from "@/lib/Types";
import { loggerPrefix } from "@/lib/const";
import { Toolbar } from "@/components/Toolbar";
import { StatusBar } from "@/components/StatusBar";
import { renderDetailRow } from "@/components/CardView/renderDetail";

import "./styles.css";

function CardView({ sessionContext, objects, onRequery }: SecretCardViewProps) {
  console.debug(loggerPrefix, "Rendering CardView with objects:", objects, sessionContext);

  return (
    <div className="row g-4 p-4">
      {Array.isArray(objects) &&
        objects.map((secret) => (
          <div className="col-12" key={secret.id}>
            <div className="card h-100">
              <div className="card-header d-flex justify-content-between align-items-center bg-white border-bottom-0 pb-0">
                <Toolbar sessionContext={sessionContext} secret={secret} onRequery={onRequery} />
                <span className="border rounded p-2">
                  <StatusBar secret={secret} />
                </span>
              </div>
              <div className="card-body">
                <h5 className="card-title mb-3 text-primary fw-bold text-center">
                  <a href={secret.manifestUrl} className="text-decoration-none text-primary">
                    {secret.name}
                  </a>
                </h5>
                <table className="table table-bordered table-sm align-middle mb-0">
                  <tbody>
                    {renderDetailRow("ID", secret.id, "number")}
                    {renderDetailRow("Manifest URL", secret.manifestUrl, "url")}
                    {renderDetailRow("Owner", secret.userProfile?.user?.username)}
                    {renderDetailRow("Owner Email", secret.userProfile?.user?.email)}
                    {renderDetailRow("Account Number", secret.userProfile?.account?.accountNumber)}
                    {renderDetailRow("Created", secret.createdAt, "dateTime")}
                    {renderDetailRow("Last Updated", secret.updatedAt, "dateTime")}
                    {renderDetailRow("Version", secret.version)}
                    {renderDetailRow("Description", secret.description)}
                    {renderDetailRow("Tags", secret.tags, "str[]")}
                    {renderDetailRow("Annotations", secret.annotations, "json")}
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
