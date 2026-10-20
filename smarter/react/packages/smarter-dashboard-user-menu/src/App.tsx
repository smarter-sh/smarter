/**
 * The Smarter web console's user menu.
 *
 * templates/react/dashboard-user-menu.html, which the console's navbar includes, mounts this app on
 * every page. See UserMenu.
 */
import UserMenu from "@/components/UserMenu";
import type { AppContext } from "@/lib/Types";

function App({ appContext, onSwitched }: { appContext: AppContext; onSwitched?: () => void }) {
  return <UserMenu appContext={appContext} onSwitched={onSwitched} />;
}

export default App;
