/**
 * LLM API Prompt Passthrough
 * Used to send raw JSON prompts to LLM APIs and display raw JSON responses.
 *
 */
import TabbedListView from "@/components/TabbedListView";
import type { SessionContext } from "@smarter/common";

interface AppProps {
  sessionContext: SessionContext;
}

function App({ sessionContext }: AppProps) {
  return (
    <>
      <section className="mt-5 mb-5 container" id="prompt-list">
        <TabbedListView sessionContext={sessionContext} />
      </section>
    </>
  );
}

export default App;
