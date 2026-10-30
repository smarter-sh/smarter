/**
 * CardView React Component
 *
 * This component renders connection resources as individual cards, displaying detailed information and actions for each connection.
 * It is used to present connections in a card-based layout, with modals for clone, rename, and delete actions.
 *
 * Features:
 * - Displays connection details in a visually distinct card format.
 * - Integrates action buttons for open, edit, clone, rename, and delete operations.
 * - Uses modal dialogs for clone, rename, and delete workflows (scaffolded for further logic).
 * - Supports a custom detail row renderer for flexible display of connection attributes.
 * - Accepts a custom CSS class for layout control.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for actions.
 * - title (string): Title displayed above the card list.
 * - connections (Connection[]): Array of connection objects to display.
 * - renderDetailRow (function): Function to render detail rows for connection attributes.
 *
 * Usage:
 * <CardView sessionContext={sessionContext} title="Your Connections" objects={connections} renderDetailRow={renderDetailRow} />
 *
 * This component is intended for use in views where objects are presented in a card/grid format.
 */
import type { ConnectionCardViewProps } from "@/lib/Types";
import { loggerPrefix } from "@/lib/const";
import { Toolbar } from "@/components/Toolbar";
import { StatusBar } from "@/components/StatusBar";
import { renderDetailRow } from "@/components/CardView/renderDetail";

import "@/components/CardView/styles.css";
import { AnnotationsRow, gettext, TagsRow } from "@smarter/common";

function CardView({ sessionContext, objects, onRequery, filtering }: ConnectionCardViewProps) {
  console.debug(loggerPrefix, "Rendering CardView with objects:", objects, sessionContext);

  return (
    <div className="row g-4 p-4">
      {Array.isArray(objects) &&
        objects.map((connection) => (
          <div className="col-12" key={connection.id}>
            <div className="card h-100">
              <div className="card-header d-flex justify-content-between align-items-center bg-white border-bottom-0 pb-0">
                <Toolbar sessionContext={sessionContext} connection={connection} onRequery={onRequery} />
                <span className="border rounded p-2">
                  <StatusBar connection={connection} />
                </span>
              </div>
              <div className="card-body">
                <h5 className="card-title mb-3 text-primary fw-bold text-center">
                  <a href={connection.manifestUrl} className="text-decoration-none text-primary">
                    {connection.name}
                  </a>
                </h5>
                <table className="table table-bordered table-sm align-middle mb-0">
                  <tbody>
                    {renderDetailRow(gettext("ID"), connection.id, "number")}
                    {renderDetailRow(gettext("Manifest URL"), connection.manifestUrl, "url")}
                    {renderDetailRow(gettext("Owner"), connection.userProfile?.user?.username)}
                    {renderDetailRow(gettext("Owner Email"), connection.userProfile?.user?.email)}
                    {renderDetailRow(gettext("Account Number"), connection.userProfile?.account?.accountNumber)}
                    {renderDetailRow(gettext("Created"), connection.createdAt, "dateTime")}
                    {renderDetailRow(gettext("Last Updated"), connection.updatedAt, "dateTime")}
                    {renderDetailRow(gettext("Version"), connection.version)}
                    {renderDetailRow(gettext("Description"), connection.description)}
                    <TagsRow tags={connection.tags} filtering={filtering} />
                    <AnnotationsRow annotations={connection.annotations} filtering={filtering} />
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
