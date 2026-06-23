/**
 * CardView React Component
 *
 * This component renders proxy resources as individual cards, displaying detailed information and actions for each proxy.
 * It is used to present proxies in a card-based layout, with modals for clone, rename, and delete actions.
 *
 * Features:
 * - Displays proxy details in a visually distinct card format.
 * - Integrates action buttons for open, edit, clone, rename, and delete operations.
 * - Uses modal dialogs for clone, rename, and delete workflows (scaffolded for further logic).
 * - Supports a custom detail row renderer for flexible display of proxy attributes.
 * - Accepts a custom CSS class for layout control.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for actions.
 * - title (string): Title displayed above the card list.
 * - proxies (Proxy[]): Array of proxy objects to display.
 * - renderDetailRow (function): Function to render detail rows for proxy attributes.
 *
 * Usage:
 * <CardView sessionContext={sessionContext} title="Your Proxies" objects={proxies} renderDetailRow={renderDetailRow} />
 *
 * This component is intended for use in views where objects are presented in a card/grid format.
 */
import type { ProxyCardViewProps } from "@/lib/Types";
import { loggerPrefix } from "@/lib/const";
import { Toolbar } from "@/components/Toolbar";
import { StatusBar } from "@/components/StatusBar";
import { renderDetailRow } from "@/components/CardView/renderDetail";

import "./styles.css";

function CardView({ sessionContext, objects, onRequery }: ProxyCardViewProps) {
  console.debug(loggerPrefix, "Rendering CardView with objects:", objects, sessionContext);

  return (
    <div className="row g-4 p-4">
      {Array.isArray(objects) &&
        objects.map((proxy) => (
          <div className="col-12" key={proxy.id}>
            <div className="card h-100">
              <div className="card-header d-flex justify-content-between align-items-center bg-white border-bottom-0 pb-0">
                <Toolbar sessionContext={sessionContext} proxy={proxy} onRequery={onRequery} />
                <span className="border rounded p-2">
                  <StatusBar proxy={proxy} />
                </span>
              </div>
              <div className="card-body">
                <h5 className="card-title mb-3 text-primary fw-bold text-center">
                  <a href={proxy.manifestUrl} className="text-decoration-none text-primary">
                    {proxy.name}
                  </a>
                </h5>
                <table className="table table-bordered table-sm align-middle mb-0">
                  <tbody>
                    {renderDetailRow("ID", proxy.id, "number")}
                    {renderDetailRow("Manifest URL", proxy.manifestUrl, "url")}
                    {renderDetailRow("Owner", proxy.userProfile?.user?.username)}
                    {renderDetailRow("Owner Email", proxy.userProfile?.user?.email)}
                    {renderDetailRow("Account Number", proxy.userProfile?.account?.accountNumber)}
                    {renderDetailRow("Created", proxy.createdAt, "dateTime")}
                    {renderDetailRow("Last Updated", proxy.updatedAt, "dateTime")}
                    {renderDetailRow("Version", proxy.version)}
                    {renderDetailRow("Description", proxy.description)}
                    {renderDetailRow("Tags", proxy.tags, "str[]")}
                    {renderDetailRow("Annotations", proxy.annotations, "json")}
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
