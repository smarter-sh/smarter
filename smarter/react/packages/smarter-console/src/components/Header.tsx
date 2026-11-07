/**
 * The console's header: the button that opens the sidebar below the lg breakpoint, the logo there, the Did you know?
 * tip from lg up while its switch is on, the theme mode menu, and the user menu. It is the theme's own header (Keen's app-header and app-navbar classes), so the theme's variables style
 * it, e.g. --bs-app-header-height.
 *
 * :param drawer: Whether the sidebar is a drawer, which the header's button opens.
 * :param onOpenSidebar: Opens the sidebar's drawer.
 */
import { gettext } from "@smarter/common";
import { UserMenu } from "@smarter/dashboard-user-menu";
import { DidYouKnow, factOfTheDay } from "@smarter/didyouknow";
import { useMemo } from "react";
import { Link, useLocation } from "react-router";

import { ThemeModeMenu } from "@/components/ThemeModeMenu";
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
  // made once per page, so that a re-render doesn't give the menu a new request id.
  const menuContext = useMemo(() => userMenuContext(session, location.pathname), [session, location.pathname]);

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
        {session.flags.didYouKnow && (
          // the theme's utility classes, so that a theme styles the tip through its variables.
          <div className="d-none d-lg-flex align-items-center min-w-0 me-5">
            <DidYouKnow
              fact={factOfTheDay(new Date())}
              classNames={{
                root: "d-flex align-items-baseline gap-2 min-w-0 text-gray-600 fs-7",
                title: "flex-shrink-0 fw-semibold text-gray-700",
                text: "text-truncate",
                link: "flex-shrink-0 link-primary",
              }}
            />
          </div>
        )}
        <div className="app-navbar flex-shrink-0 ms-auto">
          <div className="app-navbar-item ms-1 ms-md-3">
            <ThemeModeMenu />
          </div>
          <div className="app-navbar-item ms-1 ms-md-3">
            <UserMenu appContext={menuContext} onSignedOut={refreshSession} onSwitched={refreshSession} />
          </div>
        </div>
      </div>
    </header>
  );
}
