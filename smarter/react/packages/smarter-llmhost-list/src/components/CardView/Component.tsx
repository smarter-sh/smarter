/**
 * CardView React Component
 *
 * This component renders llmhost resources as individual cards, displaying detailed information and actions for each llmhost.
 * It is used to present llmhosts in a card-based layout, with modals for clone, rename, and delete actions.
 *
 * Features:
 * - Displays llmhost details in a visually distinct card format.
 * - Integrates action buttons for open, edit, clone, rename, and delete operations.
 * - Uses modal dialogs for clone, rename, and delete workflows (scaffolded for further logic).
 * - Supports a custom detail row renderer for flexible display of llmhost attributes.
 * - Accepts a custom CSS class for layout control.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for actions.
 * - title (string): Title displayed above the card list.
 * - llmhosts (LLMHost[]): Array of llmhost objects to display.
 * - renderDetailRow (function): Function to render detail rows for llmhost attributes.
 *
 * Usage:
 * <CardView sessionContext={sessionContext} title="Your LLMHosts" objects={llmhosts} renderDetailRow={renderDetailRow} />
 *
 * This component is intended for use in views where objects are presented in a card/grid format.
 */
import type { LLMHostCardViewProps } from "@/lib/Types";
import { loggerPrefix } from "@/lib/const";
import { Toolbar } from "@/components/Toolbar";
import { StatusBar } from "@/components/StatusBar";
import { renderDetailRow } from "@/components/CardView/renderDetail";

import "./styles.css";

function CardView({ sessionContext, objects, onRequery }: LLMHostCardViewProps) {
  console.debug(loggerPrefix, "Rendering CardView with objects:", objects, sessionContext);

  return (
    <div className="row g-4 p-4">
      {Array.isArray(objects) &&
        objects.map((llmhost) => (
          <div className="col-12" key={llmhost.id}>
            <div className="card h-100">
              <div className="card-header d-flex justify-content-between align-items-center bg-white border-bottom-0 pb-0">
                <Toolbar sessionContext={sessionContext} llmhost={llmhost} onRequery={onRequery} />
                <span className="border rounded p-2">
                  <StatusBar llmhost={llmhost} />
                </span>
              </div>
              <div className="card-body">
                <h5 className="card-title mb-3 text-primary fw-bold text-center">
                  <a href={llmhost.manifestUrl} className="text-decoration-none text-primary">
                    {llmhost.name}
                  </a>
                </h5>
                <table className="table table-bordered table-sm align-middle mb-0">
                  <tbody>
                    {renderDetailRow("ID", llmhost.id, "number")}
                    {renderDetailRow("Manifest URL", llmhost.manifestUrl, "url")}
                    {renderDetailRow("Base URL", llmhost.baseUrl, "url")}
                    {renderDetailRow("Owner", llmhost.userProfile?.user?.username)}
                    {renderDetailRow("Owner Email", llmhost.userProfile?.user?.email)}
                    {renderDetailRow("Account Number", llmhost.userProfile?.account?.accountNumber)}
                    {renderDetailRow("Created", llmhost.createdAt, "dateTime")}
                    {renderDetailRow("Last Updated", llmhost.updatedAt, "dateTime")}
                    {renderDetailRow("Version", llmhost.version)}
                    {renderDetailRow("Description", llmhost.description)}
                    {renderDetailRow("Tags", llmhost.tags, "str[]")}
                    {renderDetailRow("Annotations", llmhost.annotations, "json")}
                    {renderDetailRow("Ready", llmhost.ready, "bool")}
                    {renderDetailRow(
                      "RFC 1034 Compliant Name",
                      llmhost.rfc1034CompliantName
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
