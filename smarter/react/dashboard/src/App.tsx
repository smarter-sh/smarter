/**
 * LLM API Prompt Passthrough
 * Used to send raw JSON prompts to LLM APIs and display raw JSON responses.
 *
 */
import Dashboard from "./components/Dashboard";

interface AppProps {
  apiUrl: string;
}

function App({ apiUrl }: AppProps) {
  return (
    <>
      <section className="mt-5 container" id="dashboard">
        <Dashboard apiUrl={apiUrl} />
      </section>
    </>
  );
}

export default App;
