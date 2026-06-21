/**
 * LLM API Prompt Passthrough
 * Used to send raw JSON prompts to LLM APIs and display raw JSON responses.
 *
 */
import Hero from "./components/Hero";
import Prompt from "./components/Prompt";
import type { SessionContext } from "@smarter/common";


interface AppProps {
  sessionContext: SessionContext;
  defaultLLMProviderId: number;
  defaultTemplateId: number;
  providerApiUrl: string;
}

function App({ sessionContext, defaultLLMProviderId, defaultTemplateId, providerApiUrl }: AppProps) {
  return (
    <>
      <section className="mt-5 container" id="prompt-passthrough">
        <Hero />
        <Prompt
          sessionContext={sessionContext}
          defaultLLMProviderId={defaultLLMProviderId}
          defaultTemplateId={defaultTemplateId}
          providerApiUrl={providerApiUrl}
        />
      </section>
    </>
  );
}

export default App;
