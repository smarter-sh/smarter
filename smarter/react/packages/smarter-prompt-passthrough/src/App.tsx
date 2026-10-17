/**
 * LLM API Prompt Passthrough
 * Used to send raw JSON prompts to LLM APIs and display raw JSON responses.
 *
 */
import Hero from "@/components/Hero";
import Prompt from "@/components/Prompt";
import type { SessionContext } from "@smarter/common";

interface AppProps {
  sessionContext: SessionContext;
  defaultLLMProviderId: number;
  defaultTemplateId: number;
  providerApiUrl: string;
  logStreamUrl?: string;
}

function App({ sessionContext, defaultLLMProviderId, defaultTemplateId, providerApiUrl, logStreamUrl = "" }: AppProps) {
  return (
    <>
      <section className="mt-5 container" id="prompt-passthrough">
        <Hero />
        <Prompt
          sessionContext={sessionContext}
          defaultLLMProviderId={defaultLLMProviderId}
          defaultTemplateId={defaultTemplateId}
          providerApiUrl={providerApiUrl}
          logStreamUrl={logStreamUrl}
        />
      </section>
    </>
  );
}

export default App;
