/**
 * Plugin List
 * Used to display a list of available plugins.
 *
 */
import { TabbedListView } from "smarter-common";
import type { SessionContext } from "smarter-common/lib/Types";
import type { Plugin } from "@/lib/Types";

//import TabbedListView from "@/components/TabbedListView";
//import type { SessionContext } from "@/lib/Types";

interface AppProps {
  sessionContext: SessionContext<Plugin>;
}

function App({ sessionContext }: AppProps) {
  return (
    <>
      <section className="mt-5 mb-5 container" id="plugin-list">
        <TabbedListView sessionContext={sessionContext} />
      </section>
    </>
  );
}

export default App;
