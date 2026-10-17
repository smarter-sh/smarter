/**
 * Terminal
 * A bash shell inside the server's container, for superusers, in an xterm.js terminal window.
 */
import type { SessionContext } from "@smarter/common";

import Hero from "@/components/Hero";
import TerminalEmulator from "@/components/Terminal";

interface AppProps {
  sessionContext: SessionContext;
}

function App({ sessionContext }: AppProps) {
  return (
    <>
      <section className="mt-5 container" id="terminal-emulator">
        <Hero />
        <TerminalEmulator sessionContext={sessionContext} />
      </section>
    </>
  );
}

export default App;
