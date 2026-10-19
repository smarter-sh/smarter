/**
 * The server log viewer, as a component, for the web console's other React apps: the Prompt Engineer's Workbench
 * (@smarter/workbench) and the Prompt Passthrough (@smarter/prompt-passthrough) render it in their "Server Logs"
 * tabs. useLogStream() connects to the server log stream, and its records are the viewer's. main.tsx is the
 * package's development page only.
 *
 * The package's source uses relative imports, so that another package's build can import it.
 */
export { default as ServerLogs } from "./components/ServerLogs";
export type { ServerLogsProps } from "./components/ServerLogs";
export {
  DEBUG_LOG_LEVEL,
  MAX_LOG_EVENTS,
  logStreamUrlForChat,
  logStreamUrlForLevel,
  logStreamUrlForRequest,
  newRequestId,
  useLogStream,
} from "./lib/logStream";
export type { LogEvent } from "./lib/logStream";
export { LOG_WRAP_STORAGE_KEY, useLogWrap } from "./lib/logWrap";
