/**
 * LLM API Prompt Passthrough
 * Used to send raw JSON prompts to LLM APIs and display raw JSON responses.
 *
 */
import Hero from "./components/Hero";
import Prompt from "./components/Prompt";

interface AppProps {
  apiUrl: string;
  csrfCookieName: string;
  csrftoken: string;
  djangoSessionCookieName: string;
  cookieDomain: string;
  llmProviderId: string;
  templateId: string;
}

function App({
  apiUrl,
  csrfCookieName,
  csrftoken,
  djangoSessionCookieName,
  cookieDomain,
  llmProviderId,
  templateId,
}: AppProps) {
  return (
    <>
      <section className="mt-5 container" id="prompt-passthrough">
        <Hero />
        <Prompt
          apiUrl={apiUrl}
          csrfCookieName={csrfCookieName}
          csrftoken={csrftoken}
          djangoSessionCookieName={djangoSessionCookieName}
          cookieDomain={cookieDomain}
          defaultLLMProviderId={llmProviderId}
          defaultTemplateId={templateId}
        />
      </section>
    </>
  );
}

export default App;
