/**
 * CardView React Component
 *
 * This component renders orchestrator resources as individual cards, displaying detailed information and actions for each orchestrator.
 * It is used to present orchestrators in a card-based layout, with modals for clone, rename, and delete actions.
 *
 * Features:
 * - Displays orchestrator details in a visually distinct card format.
 * - Integrates action buttons for open, edit, clone, rename, and delete operations.
 * - Uses modal dialogs for clone, rename, and delete workflows (scaffolded for further logic).
 * - Supports a custom detail row renderer for flexible display of orchestrator attributes.
 * - Accepts a custom CSS class for layout control.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for actions.
 * - title (string): Title displayed above the card list.
 * - orchestrators (Orchestrator[]): Array of orchestrator objects to display.
 * - renderDetailRow (function): Function to render detail rows for orchestrator attributes.
 *
 * Usage:
 * <CardView sessionContext={sessionContext} title="Your Orchestrators" objects={orchestrators} renderDetailRow={renderDetailRow} />
 *
 * This component is intended for use in views where objects are presented in a card/grid format.
 */
import type { OrchestratorCardViewProps } from "@/lib/Types";
import { loggerPrefix } from "@/lib/const";
import { Toolbar } from "@/components/Toolbar";
import { StatusBar } from "@/components/StatusBar";
import { renderDetailRow } from "@/components/CardView/renderDetail";

import "./styles.css";

function CardView({ sessionContext, objects, onRequery }: OrchestratorCardViewProps) {
  console.debug(loggerPrefix, "Rendering CardView with objects:", objects, sessionContext);

  return (
    <div className="row g-4 p-4">
      {Array.isArray(objects) &&
        objects.map((orchestrator) => (
          <div className="col-12" key={orchestrator.id}>
            <div className="card h-100">
              <div className="card-header d-flex justify-content-between align-items-center bg-white border-bottom-0 pb-0">
                <Toolbar sessionContext={sessionContext} orchestrator={orchestrator} onRequery={onRequery} />
                <span className="border rounded p-2">
                  <StatusBar orchestrator={orchestrator} />
                </span>
              </div>
              <div className="card-body">
                <h5 className="card-title mb-3 text-primary fw-bold text-center">
                  <a href={orchestrator.manifestUrl} className="text-decoration-none text-primary">
                    {orchestrator.name}
                  </a>
                </h5>
                <table className="table table-bordered table-sm align-middle mb-0">
                  <tbody>
                    {renderDetailRow("ID", orchestrator.id, "number")}
                    {renderDetailRow("Strategy", orchestrator.strategy)}
                    {renderDetailRow("Manifest URL", orchestrator.manifestUrl, "url")}
                    {renderDetailRow("Base URL", orchestrator.baseUrl, "url")}
                    {renderDetailRow("Owner", orchestrator.userProfile?.user?.username)}
                    {renderDetailRow("Owner Email", orchestrator.userProfile?.user?.email)}
                    {renderDetailRow("Account Number", orchestrator.userProfile?.account?.accountNumber)}
                    {renderDetailRow("Created", orchestrator.createdAt, "dateTime")}
                    {renderDetailRow("Last Updated", orchestrator.updatedAt, "dateTime")}
                    {renderDetailRow("Version", orchestrator.version)}
                    {renderDetailRow("Description", orchestrator.description)}
                    {renderDetailRow("Tags", orchestrator.tags, "str[]")}
                    {renderDetailRow("Annotations", orchestrator.annotations, "json")}
                    {renderDetailRow("Ready", orchestrator.ready, "bool")}
                    {renderDetailRow(
                      "RFC 1034 Compliant Name",
                      orchestrator.rfc1034CompliantName
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
