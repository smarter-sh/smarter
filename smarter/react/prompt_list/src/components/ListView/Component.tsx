/**
 * ListView
 *
 * Renders a responsive, table-based list of chatbot resources with key details and actions.
 * Features:
 * - Displays chatbot information in a styled table with columns for name, dates, provider, model, plugins, status, and actions.
 * - Integrates Toolbar for per-chatbot actions (open, edit, clone, rename, delete).
 * - Formats dates and status using shared utilities.
 * - Shows skeleton (ghost) rows while loading, and supports incremental rendering for large lists.
 *
 * Props:
 * @param isLoading - Whether the chatbot data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param sessionContext - Authentication and API context for actions.
 * @param chatbots - Array of chatbot objects to display.
 * @param onRequery - Callback to refresh chatbot data.
 *
 * Usage:
 * <ListView
 *   sessionContext={sessionContext}
 *   chatbots={chatbots}
 *   isLoading={isLoading}
 *   ghostRows={ghostRows}
 *   onRequery={onRequery}
 * />
 *
 * Intended for views where chatbots are presented in a list/table format.
 */
import { useState, useEffect } from "react";

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

/**
 * TableHeader
 *
 * Renders the table header row for the chatbot list, including column titles for all displayed fields.
 */
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

/**
 * ChatbotRow
 *
 * Renders a single chatbot as a table row, displaying its details and action toolbar.
 *
 * @param chatbot - The chatbot object to display.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh chatbot data after an action.
 */
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

/**
 * LoadingText
 *
 * Displays a muted "Loading..." text, typically used in skeleton or ghost rows to indicate loading state.
 */
const LoadingText = () => {
  return <span className="text-muted fw-semibold">Loading...</span>;
};

/**
 * ChatbotRowGhost
 *
 * A skeleton row component to display while chatbot data is loading.
 * It mimics the structure of a regular ChatbotRow but with placeholder content.
 */
const ChatbotRowGhost = () => {
  console.debug(`${loggerPrefix} Rendering ChatbotRowGhost`);
  return (
    <tr className="ghost">
      <td className="p-1 m-0">
        <Loading />
      </td>
      <td className="d-none d-lg-table-cell width-100">
        <LoadingText />
      </td>
      <td className="d-none d-lg-table-cell width-100"></td>
      <td className=""></td>
      <td className="min-width-150"></td>
      <td className="d-none d-xl-table-cell"></td>
      <td className="d-none d-md-table-cell "></td>
      <td className="text-end "></td>
    </tr>
  );
};

/**
 * ChatbotRowGhosts
 *
 * Renders a specified number of skeleton (ghost) rows to indicate loading state in the chatbot list.
 *
 * @param count - Number of skeleton rows to render.
 */
const ChatbotRowGhosts = ({ count }: { count: number }) => {
  console.debug(`${loggerPrefix} Rendering ChatbotRowGhosts with count: ${count}`);
  return (
    <>
      {Array.from({ length: count }).map((_, idx) => (
        <ChatbotRowGhost key={idx} />
      ))}
    </>
  );
};

/**
 * ChunkedRows
 *
 * Incrementally renders chatbot rows in chunks to avoid UI blocking.
 * Uses requestIdleCallback (if available) or setTimeout as a fallback to schedule rendering.
 *
 * @param chatbots - Array of chatbot objects to render.
 * @param sessionContext - Session context for actions.
 * @param onRequery - Callback to refresh chatbot data.
 * @param chunkSize - Number of rows to render per chunk (default: 5).
 */
function ChunkedRows({
  chatbots,
  sessionContext,
  onRequery,
  chunkSize = 5,
}: {
  chatbots: Chatbot[];
  sessionContext: SessionContext;
  onRequery: () => void;
  chunkSize?: number;
}) {
  const [visibleCount, setVisibleCount] = useState(chunkSize);

  const schedule = window.requestIdleCallback || ((cb: Function) => setTimeout(cb, 0));
  const cancel = window.cancelIdleCallback || clearTimeout;

  useEffect(() => {
    let idleId: any = null;
    if (visibleCount < chatbots.length) {
      idleId = schedule(() => {
        setVisibleCount((c) => Math.min(c + chunkSize, chatbots.length));
      });
      return () => cancel(idleId);
    }
  }, [visibleCount, chatbots.length, chunkSize]);
  return (
    <>
      {chatbots.slice(0, visibleCount).map((chatbot) => (
        <ChatbotRow key={chatbot.id} chatbot={chatbot} sessionContext={sessionContext} onRequery={onRequery} />
      ))}
    </>
  );
}

/**
 * ListView
 *
 * Main component for displaying a responsive, table-based list of chatbot resources.
 * Handles loading state with skeleton rows and incremental rendering for large lists.
 *
 * @param isLoading - Whether the chatbot data is loading (shows skeleton rows if true).
 * @param ghostRows - Number of skeleton rows to display while loading.
 * @param sessionContext - Authentication and API context for actions.
 * @param chatbots - Array of chatbot objects to display.
 * @param onRequery - Callback to refresh chatbot data.
 */
export function ListView({ isLoading, ghostRows, sessionContext, chatbots, onRequery }: ListViewProps) {
  console.debug(
    `${loggerPrefix} Rendering ListView - {isLoading: ${isLoading}, ghostRows: ${ghostRows}, chatbots length: ${Array.isArray(chatbots) ? chatbots.length : "N/A"}}`,
  );
  return (
    <div className="table-responsive prompt-list-table-wrap ps-3 pe-3">
      <table className="table table-striped table-hover align-middle border">
        <TableHeader />
        <tbody>
          {isLoading ? (
            <ChatbotRowGhosts count={ghostRows} />
          ) : (
            <ChunkedRows chatbots={chatbots} sessionContext={sessionContext} onRequery={onRequery} />
          )}
        </tbody>
      </table>
    </div>
  );
}

export default ListView;
