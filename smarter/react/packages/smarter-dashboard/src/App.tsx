/**
 * LLM API Prompt Passthrough
 * Used to send raw JSON prompts to LLM APIs and display raw JSON responses.
 *
 */
import Dashboard from "./components/Dashboard";
import type { AppContextInterface } from "@/main";

function App({ appContext }: { appContext: AppContextInterface }) {
  return (
    <>
      <section className="mt-5 container" id="dashboard">
        <Dashboard appContext={appContext} />
      </section>
    </>
  );
}

export default App;
