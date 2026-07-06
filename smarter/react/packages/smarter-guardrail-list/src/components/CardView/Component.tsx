/**
 * CardView React Component
 *
 * This component renders guardrail resources as individual cards, displaying detailed information and actions for each guardrail.
 * It is used to present guardrails in a card-based layout, with modals for clone, rename, and delete actions.
 *
 * Features:
 * - Displays guardrail details in a visually distinct card format.
 * - Integrates action buttons for open, edit, clone, rename, and delete operations.
 * - Uses modal dialogs for clone, rename, and delete workflows (scaffolded for further logic).
 * - Supports a custom detail row renderer for flexible display of guardrail attributes.
 * - Accepts a custom CSS class for layout control.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for actions.
 * - title (string): Title displayed above the card list.
 * - guardrails (Guardrail[]): Array of guardrail objects to display.
 * - renderDetailRow (function): Function to render detail rows for guardrail attributes.
 *
 * Usage:
 * <CardView sessionContext={sessionContext} title="Your Guardrails" objects={guardrails} renderDetailRow={renderDetailRow} />
 *
 * This component is intended for use in views where objects are presented in a card/grid format.
 */
import type { GuardrailCardViewProps } from "@/lib/Types";
import { loggerPrefix } from "@/lib/const";
import { Toolbar } from "@/components/Toolbar";
import { StatusBar } from "@/components/StatusBar";
import { renderDetailRow } from "@/components/CardView/renderDetail";

import "./styles.css";

function CardView({ sessionContext, objects, onRequery }: GuardrailCardViewProps) {
  console.debug(loggerPrefix, "Rendering CardView with objects:", objects, sessionContext);

  return (
    <div className="row g-4 p-4">
      {Array.isArray(objects) &&
        objects.map((guardrail) => (
          <div className="col-12" key={guardrail.id}>
            <div className="card h-100">
              <div className="card-header d-flex justify-content-between align-items-center bg-white border-bottom-0 pb-0">
                <Toolbar sessionContext={sessionContext} guardrail={guardrail} onRequery={onRequery} />
                <span className="border rounded p-2">
                  <StatusBar guardrail={guardrail} />
                </span>
              </div>
              <div className="card-body">
                <h5 className="card-title mb-3 text-primary fw-bold text-center">
                  <a href={guardrail.manifestUrl} className="text-decoration-none text-primary">
                    {guardrail.name}
                  </a>
                </h5>
                <table className="table table-bordered table-sm align-middle mb-0">
                  <tbody>
                    {renderDetailRow("ID", guardrail.id, "number")}
                    {renderDetailRow("Status", guardrail.status)}
                    {renderDetailRow("Manifest URL", guardrail.manifestUrl, "url")}
                    {renderDetailRow("Base URL", guardrail.baseUrl, "url")}
                    {renderDetailRow("Owner", guardrail.userProfile?.user?.username)}
                    {renderDetailRow("Owner Email", guardrail.userProfile?.user?.email)}
                    {renderDetailRow("Account Number", guardrail.userProfile?.account?.accountNumber)}
                    {renderDetailRow("Created", guardrail.createdAt, "dateTime")}
                    {renderDetailRow("Last Updated", guardrail.updatedAt, "dateTime")}
                    {renderDetailRow("Version", guardrail.version)}
                    {renderDetailRow("Description", guardrail.description)}
                    {renderDetailRow("Tags", guardrail.tags, "str[]")}
                    {renderDetailRow("Annotations", guardrail.annotations, "json")}
                    {renderDetailRow("Ready", guardrail.ready, "bool")}
                    {renderDetailRow(
                      "RFC 1034 Compliant Name",
                      guardrail.rfc1034CompliantName
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
