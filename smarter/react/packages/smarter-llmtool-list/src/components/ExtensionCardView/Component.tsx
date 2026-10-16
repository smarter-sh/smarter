/**
 * ExtensionCardView React Component
 *
 * This component renders the installed Extensions that the user's account may use as individual,
 * read-only cards, for the Extensions tab. It has the layout of the LLMTool CardView, without its
 * Toolbar: superusers manage extensions in the Extensions console.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context.
 * - objects (Extension[]): Array of Extension objects to display.
 *
 * Usage:
 * <ExtensionCardView sessionContext={sessionContext} objects={extensions} onRequery={onRequery} />
 */
import type { ExtensionCardViewProps } from "@/lib/Types";
import { loggerPrefix } from "@/lib/const";
import { ExtensionStatusBar } from "@/components/ExtensionStatusBar";
import { renderDetailRow } from "@/components/CardView/renderDetail";

import "@/components/CardView/styles.css";

function ExtensionCardView({ objects }: ExtensionCardViewProps) {
  console.debug(loggerPrefix, "Rendering ExtensionCardView with objects:", objects);

  return (
    <div className="row g-4 p-4">
      {Array.isArray(objects) &&
        objects.map((extension) => (
          <div className="col-12" key={extension.id}>
            <div className="card h-100">
              <div className="card-header d-flex justify-content-end align-items-center bg-white border-bottom-0 pb-0">
                <span className="border rounded p-2">
                  <ExtensionStatusBar extension={extension} />
                </span>
              </div>
              <div className="card-body">
                <h5 className="card-title mb-3 text-primary fw-bold text-center">{extension.displayName}</h5>
                <table className="table table-bordered table-sm align-middle mb-0">
                  <tbody>
                    {renderDetailRow("ID", extension.id, "number")}
                    {renderDetailRow("Slug", extension.slug)}
                    {renderDetailRow("Version", extension.version)}
                    {renderDetailRow("Description", extension.description)}
                    {renderDetailRow("Publisher", extension.publisher)}
                    {renderDetailRow("Trust Badge", extension.trustBadgeLabel)}
                    {renderDetailRow("Source", extension.source)}
                    {renderDetailRow("Enabled", extension.enabled, "bool")}
                    {renderDetailRow("License", extension.license)}
                    {renderDetailRow("Homepage", extension.homepage, "url")}
                    {renderDetailRow("Installed", extension.createdAt, "dateTime")}
                    {renderDetailRow("Last Updated", extension.updatedAt, "dateTime")}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        ))}
    </div>
  );
}

export default ExtensionCardView;
