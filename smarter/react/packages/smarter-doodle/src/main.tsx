/**
 * The entry point of the Doodle's dev page, index.html, which `npm run dev` serves to show the Doodle on
 * its own. In the console, @smarter/console imports the component from src/index.ts instead.
 */
import { createRoot } from "react-dom/client";

import App from "@/App";
import { loggerPrefix } from "@/lib/const";
import type { AppContext } from "@/lib/Types";

const rootEl = document.getElementById("smarter-doodle-root");
if (!rootEl) throw new Error("Root element not found");

const apiUrl = rootEl.getAttribute("smarter-doodle-api-url");
if (!apiUrl) throw new Error("Doodle API URL not found in root element attributes");

const appContext: AppContext = {
  apiUrl,
  baseImageUrl: rootEl.getAttribute("smarter-doodle-base-image-url") || "",
  homeUrl: rootEl.getAttribute("smarter-doodle-home-url") || "/",
  logoUrl: rootEl.getAttribute("smarter-doodle-logo-url") || "",
  productName: rootEl.getAttribute("smarter-doodle-product-name") || "",
  productDescription: rootEl.getAttribute("smarter-doodle-product-description") || "",
  projectUrl: rootEl.getAttribute("smarter-doodle-project-url") || "",
};

console.debug(`${loggerPrefix} rendering the doodle of the day.`);
createRoot(rootEl).render(<App appContext={appContext} />);
