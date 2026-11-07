/**
 * The development page of the Prompt Passthrough (`npm run dev`), with the example session context of
 * src/mocks/fixtures.ts. It calls the Django dev server's api, through vite.config.ts's proxy, as the signed-in
 * user of localhost:9357. In the web console, @smarter/console renders the package's component (src/index.ts).
 */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { PROVIDER_API_URL, sessionContext } from "./mocks/fixtures";

const rootEl = document.getElementById("smarter-prompt-passthrough-root");
if (!rootEl) throw new Error("The Prompt Passthrough's root element was not found.");

createRoot(rootEl).render(
  <StrictMode>
    <App
      sessionContext={sessionContext}
      defaultLLMProviderId={1}
      defaultTemplateId={1}
      providerApiUrl={PROVIDER_API_URL}
      logStreamUrl="/api/web/dashboard/logs/stream/"
    />
  </StrictMode>,
);
