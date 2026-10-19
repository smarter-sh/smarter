/**
 * The development page of the server log viewer (`npm run dev`), which displays the example records of
 * src/mocks/fixtures.ts. In the web console, the Prompt Engineer's Workbench and the Prompt Passthrough render the
 * package's component (src/index.ts) in their "Server Logs" tabs.
 */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import ServerLogs from "./components/ServerLogs";
import { bulkLogs, jsonLog, liveLog } from "./mocks/fixtures";

const rootEl = document.getElementById("smarter-serverlogs-root");
if (!rootEl) throw new Error("The server log viewer's root element was not found.");

createRoot(rootEl).render(
  <StrictMode>
    <ServerLogs logs={[...bulkLogs, jsonLog, liveLog]} connected error={null} />
  </StrictMode>,
);
