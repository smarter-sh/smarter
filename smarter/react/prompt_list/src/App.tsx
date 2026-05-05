/**
 * LLM API Prompt Passthrough
 * Used to send raw JSON prompts to LLM APIs and display raw JSON responses.
 *
 */
import Prompts from "./components/Prompts";

interface AppProps {
  myResourcesApiUrl: string;
  csrfCookieName: string;
  csrftoken: string;
  djangoSessionCookieName: string;
  cookieDomain: string;
}

function App({ myResourcesApiUrl, csrfCookieName, csrftoken, djangoSessionCookieName, cookieDomain }: AppProps) {
  return (
    <>
      <section className="mt-5 container" id="prompt-list">
        <Prompts
          myResourcesApiUrl={myResourcesApiUrl}
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
