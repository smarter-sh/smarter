/**
 * The console's header: the button that opens the sidebar below the lg breakpoint, the logo there, and the user
 * menu. It is the theme's own header (Keen's app-header and app-navbar classes), so the theme's variables style
 * it, e.g. --bs-app-header-height.
 *
 * :param drawer: Whether the sidebar is a drawer, which the header's button opens.
 * :param onOpenSidebar: Opens the sidebar's drawer.
 */
import { gettext } from "@smarter/common";
import { UserMenu } from "@smarter/dashboard-user-menu";
import { Link, useLocation } from "react-router";

import type { ConsoleSession } from "@/contract.gen";
import { userMenuContext } from "@/lib/userMenu";
import { useConsoleSession } from "@/session/context";

interface HeaderProps {
  session: ConsoleSession;
  drawer: boolean;
  onOpenSidebar: () => void;
}

export function Header({ session, drawer, onOpenSidebar }: HeaderProps) {
  const { refresh } = useConsoleSession();
  const location = useLocation();
  // the session after signing out is a visitor's, and RequireAuth sends them to the sign-in page.
  const refreshSession = () => void refresh();

  return (
    <header id="kt_app_header" className="app-header">
      <div className="app-container container-fluid d-flex align-items-stretch justify-content-between">
        {drawer && (
          <div className="d-flex align-items-center me-3">
            <button
              type="button"
              className="btn btn-icon btn-active-color-primary w-35px h-35px"
              aria-label={gettext("Show the sidebar")}
              aria-controls="kt_app_sidebar"
              onClick={onOpenSidebar}
            >
              <i className="ki-outline ki-abstract-14 fs-2" aria-hidden="true" />
            </button>
            <Link to="/" className="ms-3" aria-label={session.branding.productName}>
              <img alt="" src={session.branding.logoUrl} className="h-25px" />
            </Link>
          </div>
        )}
        <div className="app-navbar flex-shrink-0 ms-auto">
          <div className="app-navbar-item ms-1 ms-md-3">
            <UserMenu
              appContext={userMenuContext(session, location.pathname)}
              onSignedOut={refreshSession}
              onSwitched={refreshSession}
            />
          </div>
        </div>
      </div>
    </header>
  );
}
