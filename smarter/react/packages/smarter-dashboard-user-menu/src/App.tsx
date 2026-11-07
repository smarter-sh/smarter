/**
 * The Smarter web console's user menu.
 *
 * main.tsx renders it on the package's development page. In the web console, @smarter/console renders
 * UserMenu in its header, from its session. See UserMenu.
 */
import UserMenu from "./components/UserMenu";
import type { AppContext } from "./lib/Types";

function App({ appContext, onSwitched }: { appContext: AppContext; onSwitched?: () => void }) {
  return <UserMenu appContext={appContext} onSwitched={onSwitched} />;
}

export default App;
