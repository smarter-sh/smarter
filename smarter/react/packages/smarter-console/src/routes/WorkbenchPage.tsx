/**
 * The Prompt Engineer's Workbench of an LLMClient, /workbench/llm-clients/:id/prompt: @smarter/workbench's component,
 * the chat with the LLMClient and the developer Console beside it, configured from the hashed id and the console's
 * session. The page asks the resource api for the LLMClient first, and shows Page not found when it answers 404: an
 * unknown LLMClient, another account's, or a staff-only one for a user who isn't the platform's staff, by the rule of
 * the console's manifest pages.
 */
import { gettext } from "@smarter/common";
import { Workbench } from "@smarter/workbench";
import { useMemo } from "react";
import { useNavigate, useParams } from "react-router";

import { useResource } from "@/lib/useResource";
import { onboardingContext } from "@/lib/welcome";
import { llmclientLocator, workbenchConfig } from "@/lib/workbench";
import { NotFoundPage } from "@/routes/NotFoundPage";
import { useConsoleSession } from "@/session/context";

export function WorkbenchPage() {
  const { session } = useConsoleSession();
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const loaded = useResource(llmclientLocator(id));
  // made once per session and LLMClient, so that the workbench's chat isn't reconfigured on every render.
  const workbench = useMemo(
    () => (session ? workbenchConfig(session, id, (url) => void navigate(url)) : null),
    [session, id, navigate],
  );
  const onboarding = useMemo(() => (session ? onboardingContext(session) : null), [session]);

  if (!session || !workbench) return null;
  if (loaded.state === "loading") {
    return (
      <p role="status" className="mt-5">
        {gettext("Loading...")}
      </p>
    );
  }
  if (loaded.state === "not-found") return <NotFoundPage />;
  if (loaded.state === "error") {
    return (
      <div role="alert" className="alert alert-danger mt-5">
        {gettext("The LLMClient could not be loaded.")}
      </div>
    );
  }
  return (
    <section aria-label={gettext("Chat with your AI assistant")} className="smarter-chat-section">
      <div style={{ height: "88vh" }}>
        <Workbench workbench={workbench} onboarding={onboarding} />
      </div>
    </section>
  );
}
