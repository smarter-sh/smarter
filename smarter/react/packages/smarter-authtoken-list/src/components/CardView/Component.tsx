/**
 * CardView React Component
 *
 * This component renders authtoken resources as individual cards, displaying detailed information and actions for each authtoken.
 * It is used to present authtokens in a card-based layout, with modals for clone, rename, and delete actions.
 *
 * Features:
 * - Displays authtoken details in a visually distinct card format.
 * - Integrates action buttons for open, edit, clone, rename, and delete operations.
 * - Uses modal dialogs for clone, rename, and delete workflows (scaffolded for further logic).
 * - Supports a custom detail row renderer for flexible display of authtoken attributes.
 * - Accepts a custom CSS class for layout control.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for actions.
 * - title (string): Title displayed above the card list.
 * - authtokens (AuthToken[]): Array of authtoken objects to display.
 * - renderDetailRow (function): Function to render detail rows for authtoken attributes.
 *
 * Usage:
 * <CardView sessionContext={sessionContext} title="Your AuthTokens" objects={authtokens} renderDetailRow={renderDetailRow} />
 *
 * This component is intended for use in views where objects are presented in a card/grid format.
 */
import type { AuthTokenCardViewProps } from "@/lib/Types";
import { loggerPrefix } from "@/lib/const";
import { Toolbar } from "@/components/Toolbar";
import { StatusBar } from "@/components/StatusBar";
import { renderDetailRow } from "@/components/CardView/renderDetail";

import "@/components/CardView/styles.css";
import { AnnotationsRow, gettext, TagsRow } from "@smarter/common";

function CardView({ sessionContext, objects, onRequery, filtering }: AuthTokenCardViewProps) {
  console.debug(loggerPrefix, "Rendering CardView with objects:", objects, sessionContext);

  return (
    <div className="row g-4 p-4">
      {Array.isArray(objects) &&
        objects.map((authtoken) => (
          <div className="col-12" key={authtoken.id}>
            <div className="card h-100">
              <div className="card-header d-flex justify-content-between align-items-center bg-white border-bottom-0 pb-0">
                <Toolbar sessionContext={sessionContext} authtoken={authtoken} onRequery={onRequery} />
                <span className="border rounded p-2">
                  <StatusBar authtoken={authtoken} />
                </span>
              </div>
              <div className="card-body">
                <h5 className="card-title mb-3 text-primary fw-bold text-center">
                  <a href={authtoken.manifestUrl} className="text-decoration-none text-primary">
                    {authtoken.name}
                  </a>
                </h5>
                <table className="table table-bordered table-sm align-middle mb-0">
                  <tbody>
                    {renderDetailRow(gettext("ID"), authtoken.id, "number")}
                    {renderDetailRow(gettext("Manifest URL"), authtoken.manifestUrl, "url")}
                    {renderDetailRow(gettext("Owner"), authtoken.userProfile?.user?.username)}
                    {renderDetailRow(gettext("Owner Email"), authtoken.userProfile?.user?.email)}
                    {renderDetailRow(gettext("Account Number"), authtoken.userProfile?.account?.accountNumber)}
                    {renderDetailRow(gettext("Created"), authtoken.createdAt, "dateTime")}
                    {renderDetailRow(gettext("Last Updated"), authtoken.updatedAt, "dateTime")}
                    {renderDetailRow(gettext("Version"), authtoken.version)}
                    {renderDetailRow(gettext("Description"), authtoken.description)}
                    <TagsRow tags={authtoken.tags} filtering={filtering} />
                    <AnnotationsRow annotations={authtoken.annotations} filtering={filtering} />
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
