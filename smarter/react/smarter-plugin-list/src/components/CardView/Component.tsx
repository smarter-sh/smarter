/**
 * CardView React Component
 *
 * This component renders plugin resources as individual cards, displaying detailed information and actions for each plugin.
 * It is used to present plugins in a card-based layout, with modals for clone, rename, and delete actions.
 *
 * Features:
 * - Displays plugin details in a visually distinct card format.
 * - Integrates action buttons for open, edit, clone, rename, and delete operations.
 * - Uses modal dialogs for clone, rename, and delete workflows (scaffolded for further logic).
 * - Supports a custom detail row renderer for flexible display of plugin attributes.
 * - Accepts a custom CSS class for layout control.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for actions.
 * - title (string): Title displayed above the card list.
 * - plugins (Plugin[]): Array of plugin objects to display.
 * - renderDetailRow (function): Function to render detail rows for plugin attributes.
 *
 * Usage:
 * <CardView sessionContext={sessionContext} title="Your Plugins" objects={plugins} renderDetailRow={renderDetailRow} />
 *
 * This component is intended for use in views where objects are presented in a card/grid format.
 */
import type { PluginCardViewProps } from "@/lib/Types";
import { loggerPrefix } from "@/const";
import { Toolbar } from "@/components/Toolbar";
import { StatusBar } from "@/components/StatusBar";
import { renderDetailRow } from "@/components/CardView/renderDetail";

import "./styles.css";


function CardView({ sessionContext, objects, onRequery }: PluginCardViewProps) {
  console.debug(loggerPrefix, "Rendering CardView with objects:", objects, sessionContext);

  return (
    <div className="row g-4 p-4">
      {Array.isArray(objects) &&
        objects.map((plugin) => (
          <div className="col-12" key={plugin.id}>
            <div className="card h-100">
              <div className="card-header d-flex justify-content-between align-items-center bg-white border-bottom-0 pb-0">
                <Toolbar sessionContext={sessionContext} plugin={plugin} onRequery={onRequery} />
                <span className="border rounded p-2">
                  <StatusBar plugin={plugin} />
                </span>
              </div>
              <div className="card-body">
                <h5 className="card-title mb-3 text-primary fw-bold text-center">
                  <a href={plugin.manifestUrl} className="text-decoration-none text-primary">
                    {plugin.name}
                  </a>
                </h5>
                <table className="table table-bordered table-sm align-middle mb-0">
                  <tbody>
                    {renderDetailRow("ID", plugin.id, "number")}
                    {renderDetailRow("Manifest URL", plugin.manifestUrl, "url")}
                    {renderDetailRow("Owner", plugin.userProfile?.user?.username)}
                    {renderDetailRow("Owner Email", plugin.userProfile?.user?.email)}
                    {renderDetailRow("Account Number", plugin.userProfile?.account?.accountNumber)}
                    {renderDetailRow("Created", plugin.createdAt, "dateTime")}
                    {renderDetailRow("Last Updated", plugin.updatedAt, "dateTime")}
                    {renderDetailRow("Version", plugin.version)}
                    {renderDetailRow("Description", plugin.description)}
                    {renderDetailRow("Plugin Class", plugin.pluginClass)}
                    {renderDetailRow("Tags", plugin.tags, "str[]")}
                    {renderDetailRow("Annotations", plugin.annotations, "json")}

                    {renderDetailRow("Selector Directive", plugin.selector.directive)}
                    {renderDetailRow("Selector Search Terms", plugin.selector.searchTerms ?? [], "str[]")}

                    {renderDetailRow("Prompt Provider", plugin.prompt.provider)}
                    {renderDetailRow("Prompt System Role", plugin.prompt.systemRole)}
                    {renderDetailRow("Prompt Model", plugin.prompt.model)}
                    {renderDetailRow("Prompt Temperature", plugin.prompt.temperature, "number")}
                    {renderDetailRow("Prompt Max Tokens", plugin.prompt.maxTokens, "number")}

                    {renderDetailRow("Static Data", plugin.staticData, "json")}
                    {renderDetailRow("SQL Data", plugin.sqlData, "json")}
                    {renderDetailRow("API Data", plugin.apiData, "json")}
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
