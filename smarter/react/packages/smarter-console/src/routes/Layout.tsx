/**
 * The frame of the console's signed-in pages: a header with the product, the user and their account, and
 * the page itself below it. The sidebar and the user menu move in as the console's pages do.
 */
import { gettext } from "@smarter/common";
import { useState } from "react";
import { Link, Outlet } from "react-router";

import { signOut } from "@/lib/account";
import { loggerPrefix } from "@/lib/const";
import { useConsoleSession } from "@/session/context";

export function Layout() {
  const { session, replace, refresh } = useConsoleSession();
  const [signingOut, setSigningOut] = useState(false);
  if (!session) return null;
  const { branding, user, account } = session;

  async function handleSignOut() {
    if (!session) return;
    setSigningOut(true);
    try {
      // the visitor's session sends RequireAuth to the sign-in page.
      replace(await signOut(session.cookies));
    } catch (e) {
      console.error(`${loggerPrefix} Layout could not sign out:`, e);
      await refresh();
      setSigningOut(false);
    }
  }
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
        {user && (
          <button
            type="button"
            className="btn btn-sm btn-light"
            disabled={signingOut}
            onClick={() => void handleSignOut()}
          >
            {gettext("Sign Out")}
          </button>
        )}
      </header>
      <main className="flex-grow-1 p-6">
        <Outlet />
      </main>
      <footer className="px-6 py-4 border-top text-gray-600 fs-7">{branding.copyright}</footer>
    </div>
  );
}
