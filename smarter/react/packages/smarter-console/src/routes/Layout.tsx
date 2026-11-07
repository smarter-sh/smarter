/**
 * The frame of the console's signed-in pages: the header with the user menu, the sidebar, the page, and the
 * footer. It is the theme's own app layout, the one the backend's templates/dashboard/base.html renders, so that a
 * theme styles both alike through its variables. See lib/theme.
 */
import { useEffect, useState } from "react";
import { Outlet } from "react-router";

import { Header } from "@/components/Header";
import { Sidebar } from "@/components/Sidebar";
import { useAppLayout, useBelowLg } from "@/lib/theme";
import { useConsoleSession } from "@/session/context";

export function Layout() {
  const { session } = useConsoleSession();
  const drawer = useBelowLg();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  useAppLayout();

  // Escape closes the sidebar's drawer.
  useEffect(() => {
    if (!sidebarOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSidebarOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [sidebarOpen]);

  if (!session) return null;

  return (
    <div id="kt_app_root" className="d-flex flex-column flex-root app-root">
      <div id="kt_app_page" className="app-page flex-column flex-column-fluid">
        <Header session={session} drawer={drawer} onOpenSidebar={() => setSidebarOpen(true)} />
        <div id="kt_app_wrapper" className="app-wrapper flex-column flex-row-fluid">
          <Sidebar
            session={session}
            drawer={drawer}
            open={drawer && sidebarOpen}
            onClose={() => setSidebarOpen(false)}
          />
          <div id="kt_app_main" className="app-main flex-column flex-row-fluid">
            <main id="kt_app_content" className="app-content flex-column-fluid">
              <div id="kt_app_content_container" className="app-container container-xxl">
                <Outlet />
              </div>
            </main>
            <footer id="kt_app_footer" className="app-footer">
              <div className="app-container container-fluid d-flex align-items-center py-3 text-gray-600 fs-7">
                {session.branding.copyright}
              </div>
            </footer>
          </div>
        </div>
      </div>
    </div>
  );
}
