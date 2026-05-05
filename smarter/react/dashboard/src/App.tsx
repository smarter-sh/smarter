/**
 * LLM API Prompt Passthrough
 * Used to send raw JSON prompts to LLM APIs and display raw JSON responses.
 *
 */
import Dashboard from "./components/Dashboard";

interface AppProps {
  myResourcesApiUrl: string;
  serviceHealthApiUrl: string;
  csrfCookieName: string;
  csrftoken: string;
  djangoSessionCookieName: string;
  cookieDomain: string;
}

function App({ myResourcesApiUrl, serviceHealthApiUrl, csrfCookieName, csrftoken, djangoSessionCookieName, cookieDomain }: AppProps) {
  return (
    <>
      <section className="mt-5 container" id="dashboard">
        <Dashboard
          myResourcesApiUrl={myResourcesApiUrl}
          serviceHealthApiUrl={serviceHealthApiUrl}
          csrfCookieName={csrfCookieName}
          csrftoken={csrftoken}
          djangoSessionCookieName={djangoSessionCookieName}
          cookieDomain={cookieDomain}
        />
      </section>
    </>
  );
}

export default App;
