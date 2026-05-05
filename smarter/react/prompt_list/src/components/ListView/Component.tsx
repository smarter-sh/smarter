import type { Chatbot } from "@/lib/Types";
import { pluginsText } from "@/lib/pluginsText";
import { statusCell } from "@/lib/statusCell";
import { formatDateTime } from "@/lib/formatDateTime";

import "./styles.css";

interface ListViewProps {
  title: string;
  chatbots: Chatbot[];
  cardClassName: string;
}

export function ListView({ title, chatbots, cardClassName }: ListViewProps) {
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
              <th />
              <th />
            </tr>
          </thead>
          <tbody>
            {chatbots.map((chatbot) => (
              <tr key={chatbot.id}>
                <td className="name-col p-3">
                  <a href={chatbot.urls.chat}>
                    {chatbot.name}
                    {chatbot.version ? ` v${chatbot.version}` : ""}
                  </a>
                </td>
                <td className="width-100">
                  {formatDateTime(chatbot.createdAt)}
                </td>
                <td className="width-100">
                  {formatDateTime(chatbot.updatedAt)}
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
                <td>
                  <a
                    href={chatbot.urls.chat}
                    className="btn btn-sm btn-primary"
                  >
                    Open
                  </a>
                </td>
                <td className="p-3">
                  <a
                    href={chatbot.urls.manifest}
                    className="btn btn-sm btn-info"
                  >
                    Manifest
                  </a>
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
