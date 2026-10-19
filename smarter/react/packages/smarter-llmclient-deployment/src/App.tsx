/**
 * An LLMClient's deployment page: at the deployed LLMClient's url (public), or in the "Deployment" tab
 * of the workbench's Console (workbench), which adds the LLMClient's owner, and manages its api key.
 * The workbench's api key actions answer with the page as it now is, which replaces this one.
 */
import { useState } from "react";

import ChatSessions from "./components/ChatSessions";
import Hero from "./components/Hero";
import HowThisUrlWorks from "./components/HowThisUrlWorks";
import ManifestSection from "./components/ManifestSection";
import NextSteps from "./components/NextSteps";
import SecureUrl from "./components/SecureUrl";
import SmarterProject, { EndpointsPageNote } from "./components/SmarterProject";
import type { DeploymentContext } from "./lib/types";
import "./styles.css";

export default function App({ context }: { context: DeploymentContext }) {
  const [page, setPage] = useState(context.page);
  const isPublic = page.mode === "public";
  return (
    <div className={`smarter-page d-flex flex-column w-100${isPublic ? " bg-body" : ""}`}>
      <main>
        <Hero page={page} />
        <NextSteps page={page} />
        <SecureUrl page={page} session={context.session} onPage={setPage} />
        <HowThisUrlWorks page={page} />
        <ChatSessions page={page} />
        <ManifestSection page={page} />
        {!isPublic && <EndpointsPageNote />}
      </main>
      {isPublic && <SmarterProject page={page} />}
    </div>
  );
}
