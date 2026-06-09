/**
 * LLM API Prompt Passthrough
 * Used to send raw JSON prompts to LLM APIs and display raw JSON responses.
 *
 */
import Hero from "./components/Hero";
import Prompt from "./components/Prompt";

import type { SessionContextType } from "@/main";

interface AppProps {
  sessionContext: SessionContextType;
}

function App({ sessionContext }: AppProps) {
  return (
    <>
      <section className="mt-5 container" id="prompt-passthrough">
        <Hero />
        <Prompt
          apiUrl={sessionContext.apiUrl}
          csrfCookieName={sessionContext.csrfCookieName}
          djangoSessionCookieName={sessionContext.djangoSessionCookieName}
          cookieDomain={sessionContext.cookieDomain}
          defaultLLMProviderId={sessionContext.llmProviderId}
          defaultTemplateId={sessionContext.templateId}
          providerApiUrl={sessionContext.providerApiUrl}
        />
      </section>
    </>
  );
}

export default App;
