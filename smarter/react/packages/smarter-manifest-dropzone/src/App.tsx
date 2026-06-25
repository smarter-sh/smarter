/**
 * LLM API Prompt Passthrough
 * Used to send raw JSON prompts to LLM APIs and display raw JSON responses.
 *
 */
import DropZone from "./components/DropZone";
import type { SessionContext } from "@smarter/common";

function App({ sessionContext }: { sessionContext: SessionContext }) {
  return (
    <>
      <section className="mt-5 container" id="drop-zone">
        <DropZone sessionContext={sessionContext} />
      </section>
    </>
  );
}

export default App;
