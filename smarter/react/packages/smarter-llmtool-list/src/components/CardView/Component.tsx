/**
 * CardView React Component
 *
 * This component renders LLMTool resources as individual cards, displaying detailed information and actions for each LLMTool.
 * It is used to present LLMTools in a card-based layout, with modals for clone, rename, and delete actions.
 *
 * Features:
 * - Displays LLMTool details in a visually distinct card format.
 * - Integrates action buttons for open, edit, clone, rename, and delete operations.
 * - Uses modal dialogs for clone, rename, and delete workflows (scaffolded for further logic).
 * - Supports a custom detail row renderer for flexible display of LLMTool attributes.
 * - Accepts a custom CSS class for layout control.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for actions.
 * - title (string): Title displayed above the card list.
 * - llmtools (LLMTool[]): Array of LLMTool objects to display.
 * - renderDetailRow (function): Function to render detail rows for LLMTool attributes.
 *
 * Usage:
 * <CardView sessionContext={sessionContext} title="Your LLMTools" objects={llmtools} renderDetailRow={renderDetailRow} />
 *
 * This component is intended for use in views where objects are presented in a card/grid format.
 */
import type { LLMToolCardViewProps } from "@/lib/Types";
import { loggerPrefix } from "@/lib/const";
import { Toolbar } from "@/components/Toolbar";
import { StatusBar } from "@/components/StatusBar";
import { renderDetailRow } from "@/components/CardView/renderDetail";

import "@/components/CardView/styles.css";

function CardView({ sessionContext, objects, onRequery }: LLMToolCardViewProps) {
  console.debug(loggerPrefix, "Rendering CardView with objects:", objects, sessionContext);

  return (
    <div className="row g-4 p-4">
      {Array.isArray(objects) &&
        objects.map((llmtool) => (
          <div className="col-12" key={llmtool.id}>
            <div className="card h-100">
              <div className="card-header d-flex justify-content-between align-items-center bg-white border-bottom-0 pb-0">
                <Toolbar sessionContext={sessionContext} llmtool={llmtool} onRequery={onRequery} />
                <span className="border rounded p-2">
                  <StatusBar llmtool={llmtool} />
                </span>
              </div>
              <div className="card-body">
                <h5 className="card-title mb-3 text-primary fw-bold text-center">
                  <a href={llmtool.manifestUrl} className="text-decoration-none text-primary">
                    {llmtool.name}
                  </a>
                </h5>
                <table className="table table-bordered table-sm align-middle mb-0">
                  <tbody>
                    {renderDetailRow("ID", llmtool.id, "number")}
                    {renderDetailRow("Manifest URL", llmtool.manifestUrl, "url")}
                    {renderDetailRow("Owner", llmtool.userProfile?.user?.username)}
                    {renderDetailRow("Owner Email", llmtool.userProfile?.user?.email)}
                    {renderDetailRow("Account Number", llmtool.userProfile?.account?.accountNumber)}
                    {renderDetailRow("Created", llmtool.createdAt, "dateTime")}
                    {renderDetailRow("Last Updated", llmtool.updatedAt, "dateTime")}
                    {renderDetailRow("Version", llmtool.version)}
                    {renderDetailRow("Description", llmtool.description)}
                    {renderDetailRow("LLMTool Class", llmtool.pluginClass)}
                    {renderDetailRow("Tags", llmtool.tags, "str[]")}
                    {renderDetailRow("Annotations", llmtool.annotations, "json")}

                    {renderDetailRow("Selector Directive", llmtool.selector.directive)}
                    {renderDetailRow("Selector Search Terms", llmtool.selector.searchTerms ?? [], "str[]")}

                    {renderDetailRow("Prompt Provider", llmtool.prompt.provider)}
                    {renderDetailRow("Prompt System Role", llmtool.prompt.systemRole)}
                    {renderDetailRow("Prompt Model", llmtool.prompt.model)}
                    {renderDetailRow("Prompt Temperature", llmtool.prompt.temperature, "number")}
                    {renderDetailRow("Prompt Max Tokens", llmtool.prompt.maxTokens, "number")}

                    {renderDetailRow("Static Data", llmtool.staticData, "json")}
                    {renderDetailRow("SQL Data", llmtool.sqlData, "json")}
                    {renderDetailRow("API Data", llmtool.apiData, "json")}
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
