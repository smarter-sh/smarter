/**
 * The console's home page. For now it greets the user and links to the console's pages that Django still
 * serves; the dashboard moves here in phase 2 of ADR-035.
 */
import { gettext, interpolate } from "@smarter/common";

import { useConsoleSession } from "@/session/context";

export function HomePage() {
  const { session } = useConsoleSession();
  if (!session) return null;
  const name = session.user?.firstName || session.user?.username || "";
  const dashboardUrl = new URL("dashboard/", session.branding.environmentUrl).toString();
  return (
    <section>
      <h1 className="fs-2 fw-bold mb-4">{interpolate(gettext("Welcome, %(name)s"), { name })}</h1>
      <p className="text-gray-700">
        <a href={dashboardUrl}>{gettext("Open the dashboard")}</a>
      </p>
    </section>
  );
}
