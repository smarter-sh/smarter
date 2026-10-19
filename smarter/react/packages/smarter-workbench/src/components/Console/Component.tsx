/**
 * The Console: a simulated terminal beside the chat, which displays the LLMClient's configuration and the chat
 * session's tool calls, as JSON, and, when the page passes their urls, the chat session's server logs, as they
 * stream in, the LLMClient's manifest, in the manifest editor, and its deployment page.
 */
import { useEffect, useRef, useState } from "react";
import ReactJsonView from "@microlink/react-json-view";
import { gettext } from "@smarter/common";

import { consoleData, type ConsoleConfig } from "@/components/Console/data";
import DeploymentTab from "@/components/Console/DeploymentTab";
import { initialMenuItem, MenuItems, type MenuItem } from "@/components/Console/enums";
import ManifestTab from "@/components/Console/ManifestTab";
import ServerLogs from "@/components/Console/ServerLogs";
import { logStreamUrlForChat, useLogStream } from "@/lib/logStream";
import type { WorkbenchConfig } from "@/lib/types";
import "@/components/Console/styles.css";

interface ConsoleProps {
  /** The workbench's configuration, from its root element. */
  workbench: WorkbenchConfig;
  /** The LLMClient's configuration, from its config api. Null until it loads. */
  config: ConsoleConfig;
  /**
   * The minimum log level of the server logs, e.g. "DEBUG" in sandbox mode. Without it, the server's
   * own log level. A change reconnects the stream, which replays the history at the new level.
   */
  logLevel?: string | null;
  /** Changes when a new chat session starts, which clears the server logs. */
  resetKey?: number | string;
  /** Called when the manifest editor saves the manifest. */
  onManifestSaved?: () => void;
  /**
   * Called with the selected menu item, when the Console mounts, and when the user selects another,
   * e.g. so that the chat fetches the configuration's diagnostic parts for the tabs that display them.
   */
  onSelect?: (item: MenuItem) => void;
}

interface Tab {
  id: MenuItem;
  label: string;
  /** What the Console says when the chat session has no data for the tab yet. */
  empty: string;
}

/**
 * The Console's tabs, from left to right, translated, in the order of a prompt engineer's work: the manifest,
 * which each change starts with, the server logs and the tool calls, which tell what a prompt did, the
 * configuration, for reference, and the deployment, for when the work is done. Each of the manifest, the server
 * logs and the deployment is there only when the page passes its url. The server logs, when they are there, are
 * selected when the Console opens: see initialMenuItem().
 */
function tabs(withServerLogs: boolean, withManifest: boolean, withDeployment: boolean): Tab[] {
  // Translators: the tab of the Console that edits the LLMClient's YAML manifest.
  const manifest: Tab = { id: MenuItems.MANIFEST, label: gettext("Manifest"), empty: "" };
  // Translators: the tab of the Console about the LLMClient's deployment: its url, and how to use it.
  const deployment: Tab = { id: MenuItems.DEPLOYMENT, label: gettext("Deployment"), empty: "" };
  const serverLogs: Tab = { id: MenuItems.SERVER_LOGS, label: gettext("Server Logs"), empty: "" };
  const menu: Tab[] = [
    {
      id: MenuItems.CHAT_TOOL_CALL_HISTORY,
      label: gettext("Tool Calls"),
      empty: gettext("No tool calls in this chat session yet."),
    },
    {
      id: MenuItems.CHAT_CONFIG,
      // Translators: the tab of the Console that displays the chat's configuration.
      label: gettext("Config"),
      empty: gettext("No config in this chat session yet."),
    },
  ];
  return [
    ...(withManifest ? [manifest] : []),
    ...(withServerLogs ? [serverLogs] : []),
    ...menu,
    ...(withDeployment ? [deployment] : []),
  ];
}

/** The name of a tool call, as the Console displays it collapsed: its function's name. */
function toolCallName(item: object): string {
  const name = (item as { function_name?: unknown }).function_name;
  return typeof name === "string" && name ? name : "tool_call";
}

function Console({ workbench, config, logLevel = null, resetKey, onManifestSaved, onSelect }: ConsoleProps) {
  const { logStreamUrl, manifestUrl, deploymentUrl } = workbench;
  // the server logs, when there are any, are first, and selected. Their stream stays connected,
  // so that the logs keep arriving while another tab is selected.
  const [selectedMenuItem, setSelectedMenuItem] = useState<MenuItem>(() => initialMenuItem(logStreamUrl));
  useEffect(() => {
    onSelect?.(selectedMenuItem);
  }, [onSelect, selectedMenuItem]);
  // the chat session's own server logs: the records of the requests with its session key. A new chat
  // session has a new key, and so a new stream.
  const sessionKey = config?.session_key ?? null;
  const { clear: clearLogs, ...logStream } = useLogStream(logStreamUrlForChat(logStreamUrl, sessionKey, logLevel));
  const previousResetKey = useRef(resetKey);

  useEffect(() => {
    // a new chat session: its server logs start empty.
    if (resetKey === previousResetKey.current) return;
    previousResetKey.current = resetKey;
    clearLogs();
  }, [resetKey, clearLogs]);
  // the manifest editor and the deployment page load when their tab is first selected, and then stay,
  // hidden while another tab is selected, so that the editor keeps its unsaved changes, and the page its
  // scroll position.
  const [editorOpened, setEditorOpened] = useState(false);
  const [deploymentOpened, setDeploymentOpened] = useState(false);
  const menu = tabs(!!logStreamUrl, !!manifestUrl, !!deploymentUrl);
  const showEditor = selectedMenuItem === MenuItems.MANIFEST && !!manifestUrl;
  const showDeployment = selectedMenuItem === MenuItems.DEPLOYMENT && !!deploymentUrl;
  const showLogs = selectedMenuItem === MenuItems.SERVER_LOGS && !!logStreamUrl;
  const emptyText = menu.find(({ id }) => id === selectedMenuItem)?.empty ?? "";

  // a simulated bash shell.
  const [shell] = useState(() => ({
    lastLogin: new Date().toString(),
    ipAddress: `192.168.${Math.floor(Math.random() * 256)}.${Math.floor(Math.random() * 256)}`,
    prompt: `smarter_user@smarter-${Math.floor(Math.random() * 0xffffffff).toString(16)}:~/smarter$`,
  }));

  const toolCalls = selectedMenuItem === MenuItems.CHAT_TOOL_CALL_HISTORY;
  // null while the chat fetches the tab's data, which is then neither displayed nor empty.
  const loaded = consoleData(config, selectedMenuItem);
  const data = loaded ?? [];
  const isEmpty = !showLogs && loaded?.length === 0 && !!config;

  return (
    <div className="console">
      <div className="app-main flex-column flex-row-fluid" id="chatapp_console_app_main">
        <div className="d-flex flex-column flex-column-fluid">
          <div id="chatapp_console_app_content" className="app-content flex-column-fluid p-0 pb-5">
            <div id="chatapp_console_app_content_container" className="app-container container-lg">
              <nav
                id="chatapp_console"
                aria-label={gettext("Console")}
                className="bg-gray-200 d-flex flex-stack flex-wrap mb-2 p-2 console-nav-items"
              >
                <ul className="nav flex-wrap border-transparent">
                  {menu.map(({ label, id }) => (
                    <li className="nav-item my-1" key={id}>
                      <button
                        type="button"
                        id={id}
                        aria-pressed={id === selectedMenuItem}
                        className={`btn btn-sm btn-color-gray-600 bg-state-body btn-active-color-gray-800 fw-bolder fw-bold fs-6 fs-lg-base nav-link px-3 px-lg-4 mx-1 ${
                          id === selectedMenuItem ? "active" : ""
                        }`}
                        onClick={() => {
                          setSelectedMenuItem(id);
                          if (id === MenuItems.MANIFEST) setEditorOpened(true);
                          if (id === MenuItems.DEPLOYMENT) setDeploymentOpened(true);
                        }}
                      >
                        {label}
                      </button>
                    </li>
                  ))}
                </ul>
              </nav>
              {manifestUrl && editorOpened && (
                <div className="console-manifest" hidden={!showEditor}>
                  <ManifestTab workbench={workbench} onSaved={onManifestSaved} />
                </div>
              )}
              {deploymentUrl && deploymentOpened && (
                <div className="console-deployment" hidden={!showDeployment}>
                  <DeploymentTab workbench={workbench} />
                </div>
              )}
              <div
                className={`console-output rounded ${showLogs ? "console-output-logs" : ""}`}
                role="log"
                aria-label={gettext("Console output")}
                hidden={showEditor || showDeployment}
              >
                <div className="console-output-content">
                  {/* a terminal's own messages, which are in English. */}
                  <p className="mb-0">
                    Last login: {shell.lastLogin} from {shell.ipAddress}
                  </p>
                  <p className="mb-0">{shell.prompt}</p>
                  {showLogs && <ServerLogs {...logStream} />}
                  {isEmpty && <p className="mb-0 console-empty">{emptyText}</p>}
                  {data.length > 0 && (
                    <>
                      {data.map((item, index) => (
                        <ReactJsonView
                          key={index}
                          src={item}
                          theme="monokai"
                          // a tool call is collapsed, and named by its function, so that the tab lists them.
                          name={toolCalls ? toolCallName(item) : undefined}
                          // the configuration is collapsed to its top-level keys.
                          collapsed={toolCalls || 1}
                        />
                      ))}
                      <p className="mb-0">{shell.prompt}</p>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Console;
