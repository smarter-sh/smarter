/**
 * LLM API Prompt Passthrough
 * Used to send raw JSON prompts to LLM APIs and display raw JSON responses.
 *
 */
import Hero from "./components/Hero";
import TerminalEmulator from "./components/Terminal";

interface AppProps {
  apiUrl: string;
  csrfCookieName: string;
  csrftoken: string;
  djangoSessionCookieName: string;
  cookieDomain: string;
}

function App({
  apiUrl,
  csrfCookieName,
  csrftoken,
  djangoSessionCookieName,
  cookieDomain,
}: AppProps) {
  return (
    <>
      <section className="mt-5 container" id="terminal-emulator">
        <Hero />
        <TerminalEmulator
          apiUrl={apiUrl}
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
