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
 * - cardClassName (string): CSS class for the outer container, allowing layout customization.
 *
 * Usage:
 * <ListView sessionContext={sessionContext} title="Your Chatbots" chatbots={chatbots} cardClassName="mt-15" />
 *
 * This component is intended for use in views where chatbots are presented in a list/table format.
 */
import type { Chatbot, SessionContext } from "@/lib/Types";
import { pluginsText } from "@/lib/pluginsText";
import { statusCell } from "@/lib/statusCell";
import { formatDateTime } from "@/lib/formatDateTime";
import { Toolbar } from "@/components/Toolbar"

import "./styles.css";


interface ListViewProps {
  sessionContext: SessionContext;
  title: string;
  chatbots: Chatbot[];
  cardClassName: string;
}

export function ListView({ sessionContext, title, chatbots, cardClassName }: ListViewProps) {
  return (
    <div className={cardClassName}>
      <div className="prompt-list-heading-wrap">
        <h3 className="text-center">{title}</h3>
      </div>
      <div className="table-responsive prompt-list-table-wrap">
        <table className="table table-striped table-hover align-middle">
          <thead className="table-light">
            <tr>
              <th className="p-3">Name</th>
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
                <td className="name-col p-3">
                  <a href={chatbot.urlChatapp}>
                    {chatbot.name}
                    {chatbot.version ? ` v${chatbot.version}` : ""}
                  </a>
                </td>
                <td className="width-100">
                  {formatDateTime(chatbot.createdAt, "date")}
                </td>
                <td className="width-100">
                  {formatDateTime(
                    chatbot.updatedAt,
                    "relative",
                    chatbot.createdAt,
                  )}
                </td>
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
                <td className="min-width-150">
                  {chatbot.defaultModel || "default"}
                </td>
                <td>{pluginsText(chatbot)}</td>
                <td>{statusCell(chatbot)}</td>
                <td className="text-end min-width-250">
                  <Toolbar sessionContext={sessionContext} chatbot={chatbot} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default ListView;
