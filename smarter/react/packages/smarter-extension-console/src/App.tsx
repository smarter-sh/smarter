/**
 * The Smarter Extensions app: the Extensions list, or an extension's page. Superusers manage
 * extensions; everyone else sees them read-only.
 *
 * :param context: The session context of its requests, its api and list urls, the extension's slug on its page,
 *   and whether the user may manage extensions.
 * :param navigate: Goes to another of its pages, e.g. an extension's after it is installed. The single-page console
 *   passes its router's; by default, the browser loads the page.
 */
import ExtensionList from "./components/ExtensionList";
import ExtensionPage from "./components/ExtensionPage";
import type { ConsoleContext } from "./lib/types";

interface AppProps {
  context: ConsoleContext;
  navigate?: (url: string) => void;
}

export default function App({ context, navigate }: AppProps) {
  if (context.slug) return <ExtensionPage context={context} slug={context.slug} navigate={navigate} />;
  return <ExtensionList context={context} navigate={navigate} />;
}
