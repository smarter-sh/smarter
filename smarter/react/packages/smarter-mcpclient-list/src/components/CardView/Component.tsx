/**
 * CardView React Component
 *
 * This component renders mcpclient resources as individual cards, displaying detailed information and actions for each mcpclient.
 * It is used to present mcpclients in a card-based layout, with modals for clone, rename, and delete actions.
 *
 * Features:
 * - Displays mcpclient details in a visually distinct card format.
 * - Integrates action buttons for open, edit, clone, rename, and delete operations.
 * - Uses modal dialogs for clone, rename, and delete workflows (scaffolded for further logic).
 * - Supports a custom detail row renderer for flexible display of mcpclient attributes.
 * - Accepts a custom CSS class for layout control.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for actions.
 * - title (string): Title displayed above the card list.
 * - mcpclients (MCPClient[]): Array of mcpclient objects to display.
 * - renderDetailRow (function): Function to render detail rows for mcpclient attributes.
 *
 * Usage:
 * <CardView sessionContext={sessionContext} title="Your MCPClients" objects={mcpclients} renderDetailRow={renderDetailRow} />
 *
 * This component is intended for use in views where objects are presented in a card/grid format.
 */
import type { MCPClientCardViewProps } from "@/lib/Types";
import { loggerPrefix } from "@/lib/const";
import { Toolbar } from "@/components/Toolbar";
import { StatusBar } from "@/components/StatusBar";
import { renderDetailRow } from "@/components/CardView/renderDetail";

import "./styles.css";

function CardView({ sessionContext, objects, onRequery }: MCPClientCardViewProps) {
  console.debug(loggerPrefix, "Rendering CardView with objects:", objects, sessionContext);

  return (
    <div className="row g-4 p-4">
      {Array.isArray(objects) &&
        objects.map((mcpclient) => (
          <div className="col-12" key={mcpclient.id}>
            <div className="card h-100">
              <div className="card-header d-flex justify-content-between align-items-center bg-white border-bottom-0 pb-0">
                <Toolbar sessionContext={sessionContext} mcpclient={mcpclient} onRequery={onRequery} />
                <span className="border rounded p-2">
                  <StatusBar mcpclient={mcpclient} />
                </span>
              </div>
              <div className="card-body">
                <h5 className="card-title mb-3 text-primary fw-bold text-center">
                  <a href={mcpclient.manifestUrl} className="text-decoration-none text-primary">
                    {mcpclient.name}
                  </a>
                </h5>
                <table className="table table-bordered table-sm align-middle mb-0">
                  <tbody>
                    {renderDetailRow("ID", mcpclient.id, "number")}
                    {renderDetailRow("Status", mcpclient.status)}
                    {renderDetailRow("Manifest URL", mcpclient.manifestUrl, "url")}
                    {renderDetailRow("Base URL", mcpclient.baseUrl, "url")}
                    {renderDetailRow("Owner", mcpclient.userProfile?.user?.username)}
                    {renderDetailRow("Owner Email", mcpclient.userProfile?.user?.email)}
                    {renderDetailRow("Account Number", mcpclient.userProfile?.account?.accountNumber)}
                    {renderDetailRow("Created", mcpclient.createdAt, "dateTime")}
                    {renderDetailRow("Last Updated", mcpclient.updatedAt, "dateTime")}
                    {renderDetailRow("Version", mcpclient.version)}
                    {renderDetailRow("Description", mcpclient.description)}
                    {renderDetailRow("Tags", mcpclient.tags, "str[]")}
                    {renderDetailRow("Annotations", mcpclient.annotations, "json")}
                    {renderDetailRow("Ready", mcpclient.ready, "bool")}
                    {renderDetailRow(
                      "RFC 1034 Compliant Name",
                      mcpclient.rfc1034CompliantName
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
