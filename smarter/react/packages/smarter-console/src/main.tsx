/** The console's entry point: mounts the app, with the browser's router, in index.html's root element. */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter } from "react-router";

import App from "@/App";
import { routes } from "@/router";

const rootElement = document.getElementById("smarter-console-root");
if (!rootElement) throw new Error("The console's root element, #smarter-console-root, is missing.");

const router = createBrowserRouter(routes);

createRoot(rootElement).render(
  <StrictMode>
    <App router={router} />
  </StrictMode>,
);
