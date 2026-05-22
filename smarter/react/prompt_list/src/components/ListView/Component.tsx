/**
 * ListView React Component
 *
 * This component renders a table-based list of chatbot resources, displaying key details and actions for each chatbot.
 * It is used to present chatbots in a tabular format, with columns for name, creation and update dates, provider, model, plugins, status, and a toolbar for actions.
 *
 * Features:
 * - Displays chatbot information in a responsive, styled table.
 * - Integrates the Toolbar component for per-chatbot actions (open, edit, clone, rename, delete).
 * - Formats dates and status using shared utility functions.
 * - Supports custom card class names for layout flexibility.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context for actions.
 * - title (string): Title displayed above the table.
 * - chatbots (Chatbot[]): Array of chatbot objects to display.
 *
 * Usage:
 * <ListView sessionContext={sessionContext} chatbots={chatbots} />
 *
 * This component is intended for use in views where chatbots are presented in a list/table format.
 */
import type { Chatbot, SessionContext } from "@/lib/Types";
import { pluginsText } from "@/lib/pluginsText";
import { formatDateTime } from "@/lib/formatDateTime";
import { Toolbar } from "@/components/Toolbar"
import { StatusBar } from "@/components/StatusBar";

import "./styles.css";


interface ListViewProps {
  sessionContext: SessionContext;
  chatbots: Chatbot[];
  onRequery: () => void;
}

export function ListView({ sessionContext, chatbots, onRequery }: ListViewProps) {

  return (
    <div className="table-responsive prompt-list-table-wrap">
      <table className="table table-striped table-hover align-middle">
        <thead className="table-light border-bottom-2">
          <tr className="">
            <th className="p-1">Name</th>
            <th className="width-100">Created</th>
            <th className="width-100">Updated</th>
            <th>Provider</th>
            <th className="min-width-150">Model</th>
            <th>Plugins</th>
            <th>Status</th>
            <th className="text-end min-width-250"></th>
          </tr>
        </thead>
        <tbody>
          {chatbots.map((chatbot) => (
            <tr key={chatbot.id}>
              {/* Name */}
              <td className="name-col p-1 m-0">
                <a href={chatbot.urlChatapp}>
                  {chatbot.name}
                  {chatbot.version ? ` v${chatbot.version}` : ""}
                </a>
              </td>
              {/* Created Date */}
              <td className="width-100">
                {formatDateTime(chatbot.createdAt, "date")}
              </td>
              {/* Updated Date */}
              <td className="width-100">
                {formatDateTime(
                  chatbot.updatedAt,
                  "relative",
                  chatbot.createdAt,
                )}
              </td>
              {/* Provider */}
              <td>
                {chatbot.appLogoUrl ? (
                  <img
                    src={chatbot.appLogoUrl}
                    alt={`${chatbot.provider} logo`}
                    className="provider-logo d-none"
                  />
                ) : null}
                {chatbot.provider}
              </td>
              {/* Model */}
              <td className="min-width-150">
                {chatbot.defaultModel || "default"}
              </td>
              {/* Plugins */}
              <td>{pluginsText(chatbot)}</td>
              {/* Status */}
              <td>
                <StatusBar chatbot={chatbot} />
              </td>
              {/* Actions */}
              <td className="text-end min-width-250">
                <Toolbar sessionContext={sessionContext} chatbot={chatbot} onRequery={onRequery} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default ListView;
