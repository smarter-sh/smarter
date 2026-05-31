/**
 * ListView React Component
 *
 * This component renders a table-based list of chatbot resources, displaying
 * key details and actions for each chatbot. It is used to present chatbots
 * in a tabular format, with columns for name, creation and update dates,
 * provider, model, plugins, status, and a toolbar for actions.
 *
 * Features:
 * - Displays chatbot information in a responsive, styled table.
 * - Integrates the Toolbar component for per-chatbot actions (open, edit, clone, rename, delete).
 * - Formats dates and status using shared utility functions.
 * - Supports custom card class names for layout flexibility.
 * - Supports skeleton loading (ghost rows) when data is loading, based on isLoading and ghostRows props.
 *
 * Props:
 * - isLoading (boolean): Whether the chatbot data is loading (shows skeleton rows if true).
 * - ghostRows (number): Number of skeleton rows to display while loading.
 * - sessionContext (SessionContext): Authentication and API context for actions.
 * - chatbots (Chatbot[]): Array of chatbot objects to display.
 * - onRequery (function): Callback to refresh chatbot data.
 *
 * Usage:
 * <ListView sessionContext={sessionContext} chatbots={chatbots} isLoading={isLoading} ghostRows={ghostRows} onRequery={onRequery} />
 *
 * This component is intended for use in views where chatbots are presented in a list/table format.
 */
import type { Chatbot, SessionContext } from "@/lib/Types";
import { formatDateTime } from "@/lib/formatDateTime";
import { Toolbar } from "@/components/Toolbar";
import { StatusBar } from "@/components/StatusBar";
import { loggerPrefix } from "@/const";
import Loading from "@/components/Loading";

import "./styles.css";

interface ListViewProps {
  isLoading: boolean;
  ghostRows: number;
  sessionContext: SessionContext;
  chatbots: Chatbot[];
  onRequery: () => void;
}

const TableHeader = () => {
  return (
    <thead className="table-light border-bottom-2">
      <tr className="">
        <th className=" p-1">Name</th>
        <th className="d-none d-lg-table-cell width-100">Created</th>
        <th className="d-none d-lg-table-cell width-100">Updated</th>
        <th className="">Provider</th>
        <th className="min-width-150">Model</th>
        <th className="d-none d-xl-table-cell">Plugins</th>
        <th className="d-none d-md-table-cell">Status</th>
        <th className="">Operations</th>
      </tr>
    </thead>
  );
};

const ChatbotRow = ({
  chatbot,
  sessionContext,
  onRequery,
}: {
  chatbot: Chatbot;
  sessionContext: SessionContext;
  onRequery: () => void;
}) => {
  const CreatedDate = ({ date }: { date: string }) => {
    return <span>{formatDateTime(date, "date")}</span>;
  };

  const UpdatedDate = ({ date, createdAt }: { date: string; createdAt: string }) => {
    return <span>{formatDateTime(date, "relative", createdAt)}</span>;
  };

  // A helper component to display combined plugins and functions for a chatbot
  // as a comma-separated list.
  const Plugins = ({ chatbot }: { chatbot: Chatbot }) => {
    const plugins = chatbot.plugins
      ?.map((p) => p?.name || "")
      .filter(Boolean)
      .join(", ");
    const functions = chatbot.functions
      ?.map((f) => f?.name || "")
      .filter(Boolean)
      .join(", ");
    // Combine plugins and functions into a single string
    const combined = [plugins, functions].filter(Boolean).join(", ");
    return <span>{combined}</span>;
  };

  return (
    <tr className="" key={chatbot.id}>
      {/* Name */}
      <td className="p-1 m-0">
        <a href={chatbot.urlChatapp}>{chatbot.name}</a>
      </td>
      {/* Created Date */}
      <td className="d-none d-lg-table-cell width-100">
        <CreatedDate date={chatbot.createdAt} />
      </td>
      {/* Updated Date */}
      <td className="d-none d-lg-table-cell width-100">
        <UpdatedDate date={chatbot.updatedAt} createdAt={chatbot.createdAt} />
      </td>
      {/* Provider */}
      <td className="">{chatbot.provider}</td>
      {/* Model */}
      <td className="min-width-150">{chatbot.defaultModel || "default"}</td>
      {/* Plugins */}
      <td className="d-none d-xl-table-cell">
        <Plugins chatbot={chatbot} />
      </td>
      {/* Status */}
      <td className="d-none d-md-table-cell ">
        <StatusBar chatbot={chatbot} />
      </td>
      {/* Actions */}
      <td className="text-end ">
        <Toolbar sessionContext={sessionContext} chatbot={chatbot} onRequery={onRequery} />
      </td>
    </tr>
  );
};

const LoadingText = () => {
  return <span className="text-muted fw-semibold">Loading...</span>;
}
// A skeleton row component to display while chatbot data is loading.
// It mimics the structure of a regular ChatbotRow but with placeholder content.
const ChatbotRowGhost = () => {
  console.debug(`${loggerPrefix} Rendering ChatbotRowGhost`);
  return (
    <tr className="ghost">
      <td className="p-1 m-0"><Loading /></td>
      <td className="d-none d-lg-table-cell width-100"><LoadingText /></td>
      <td className="d-none d-lg-table-cell width-100"></td>
      <td className=""></td>
      <td className="min-width-150"></td>
      <td className="d-none d-xl-table-cell"></td>
      <td className="d-none d-md-table-cell "></td>
      <td className="text-end "></td>
    </tr>
  );
};

export function ListView({ isLoading, ghostRows, sessionContext, chatbots, onRequery }: ListViewProps) {
  console.debug(
    `${loggerPrefix} Rendering ListView - {isLoading: ${isLoading}, ghostRows: ${ghostRows}, chatbots length: ${Array.isArray(chatbots) ? chatbots.length : "N/A"}}`,
  );
  return (
    <div className="table-responsive prompt-list-table-wrap ps-3 pe-3">
      <table className="table table-striped table-hover align-middle border">
        <TableHeader />
        <tbody>
          {isLoading
            ? Array.from({ length: ghostRows }).map((_, idx) => <ChatbotRowGhost key={idx} />)
            : Array.isArray(chatbots) &&
              chatbots.map((chatbot) => (
                <ChatbotRow key={chatbot.id} chatbot={chatbot} sessionContext={sessionContext} onRequery={onRequery} />
              ))}
        </tbody>
      </table>
    </div>
  );
}

export default ListView;
