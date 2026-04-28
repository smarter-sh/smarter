/**
 * LLM API Prompt Passthrough
 * Used to send raw JSON prompts to LLM APIs and display raw JSON responses.
 *
 */
import Hero from "./components/Hero";
import Prompt from "./components/Prompt";

function App({
  apiUrl,
  csrfCookieName,
  csrftoken,
  djangoSessionCookieName,
  cookieDomain,
  llmProviderId,
  templateId,
}: {
  apiUrl: string;
  csrfCookieName: string;
  csrftoken: string;
  djangoSessionCookieName: string;
  cookieDomain: string;
  llmProviderId: string;
  templateId: string;
}) {
  return (
    <>
      <section id="next-steps" className="container">
        <div className="mt-5">
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
        </div>
      </section>
    </>
  );
}

export default App;
