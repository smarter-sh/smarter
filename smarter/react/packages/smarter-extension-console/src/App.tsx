/**
 * The Smarter Extensions app: the Extensions list, or an extension's page. Superusers manage
 * extensions; everyone else sees them read-only.
 */
import ExtensionList from "@/components/ExtensionList";
import ExtensionPage from "@/components/ExtensionPage";
import type { ConsoleContext } from "@/lib/types";

export default function App({ context }: { context: ConsoleContext }) {
  return context.slug ? <ExtensionPage context={context} slug={context.slug} /> : <ExtensionList context={context} />;
}
