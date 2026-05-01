/**
 * LLM API Prompt Passthrough
 * Used to send raw JSON prompts to LLM APIs and display raw JSON responses.
 *
 */
import Hero from "./components/Hero";
import TerminalEmulator from "./components/Terminal";

interface AppProps {
  apiUrl: string;
}

function App({ apiUrl }: AppProps) {
  return (
    <>
      <section className="mt-5 container" id="terminal-emulator">
        <Hero />
        <TerminalEmulator apiUrl={apiUrl} />
      </section>
    </>
  );
}

export default App;
