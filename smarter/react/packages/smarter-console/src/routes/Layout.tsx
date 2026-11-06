/**
 * The frame of the console's signed-in pages: a header with the product, the user and their account, and
 * the page itself below it. The sidebar and the user menu move in as the console's pages do.
 */
import { gettext } from "@smarter/common";
import { Link, Outlet } from "react-router";

import { useConsoleSession } from "@/session/context";

export function Layout() {
  const { session } = useConsoleSession();
  if (!session) return null;
  const { branding, user, account } = session;
  return (
    <div className="d-flex flex-column min-vh-100">
      <header className="d-flex align-items-center gap-4 px-6 py-4 border-bottom">
        <Link to="/" className="d-flex align-items-center gap-3 text-gray-900">
          <img src={branding.logoUrl} alt="" height={32} />
          <span className="fs-4 fw-bold">{branding.productName}</span>
        </Link>
        {user && (
          <div className="ms-auto text-end">
            <div className="fw-semibold">{user.email || user.username}</div>
            {account && (
              <div className="text-gray-600 fs-7" aria-label={gettext("Account")}>
                {account.name} · {account.accountNumber}
              </div>
            )}
          </div>
        )}
      </header>
      <main className="flex-grow-1 p-6">
        <Outlet />
      </main>
      <footer className="px-6 py-4 border-top text-gray-600 fs-7">{branding.copyright}</footer>
    </div>
  );
}
