/**
 * LLM API Prompt Passthrough
 * Used to send raw JSON prompts to LLM APIs and display raw JSON responses.
 *
 */
import Prompts from "./components/Prompts";
import type { SessionContext } from "@/lib/Types";

interface AppProps {
  sessionContext: SessionContext;
}

function App({ sessionContext }: AppProps) {
  return (
    <>
      <section className="mt-5 container" id="prompt-list">
        <Prompts sessionContext={sessionContext} />
      </section>
    </>
  );
}

export default App;
