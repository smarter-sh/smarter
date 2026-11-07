/**
 * The console's sidebar: the logo, then the sections of lib/sidebar, with the links that the session's sidebar
 * has. It is the theme's own sidebar (Keen's app-sidebar and menu classes), so the theme's variables style it,
 * e.g. --bs-app-sidebar-width and --bs-app-sidebar-dark-bg-color. Below the theme's lg breakpoint it is a
 * drawer that the header's button opens.
 *
 * :param open: Whether the drawer is open, below the lg breakpoint.
 * :param drawer: Whether the sidebar is a drawer: below the lg breakpoint.
 * :param onClose: Closes the drawer, e.g. on a click outside it.
 */
import { gettext } from "@smarter/common";
import { Link, useLocation } from "react-router";

import type { ConsoleSession } from "@/contract.gen";
import { activeSidebarItem, sidebarSections, type SidebarItem } from "@/lib/sidebar";

interface SidebarProps {
  session: ConsoleSession;
  open: boolean;
  drawer: boolean;
  onClose: () => void;
}

interface ItemLinkProps {
  item: SidebarItem;
  url: string;
  active: boolean;
  /** A count beside the label, e.g. the extensions with an update; none when 0. */
  badge: number;
}

function ItemLink({ item, url, active, badge }: ItemLinkProps) {
  const external = "href" in item;
  return (
    <div className="menu-item">
      <a
        className={`menu-link${active ? " active" : ""}`}
        href={url}
        aria-current={active ? "page" : undefined}
        target={external ? "_blank" : undefined}
        rel={external ? "noreferrer" : undefined}
        data-smarter-onboarding={item.onboarding}
      >
        <span className="menu-icon">
          <i className={`ki-outline ${item.icon} fs-2`} aria-hidden="true" />
        </span>
        <span className="menu-title">{item.label}</span>
        {badge > 0 && (
          <span className="menu-badge">
            <span className="badge badge-warning" title={gettext("Updates available")}>
              {badge}
            </span>
          </span>
        )}
      </a>
    </div>
  );
}

export function Sidebar({ session, open, drawer, onClose }: SidebarProps) {
  const location = useLocation();
  const links = session.sidebar;
  if (!links) return null;
  const active = activeSidebarItem(location.pathname, links);
  const extensionUpdates = session.badges?.extensionUpdates ?? 0;

  const sections = [];
  for (const section of sidebarSections(session.branding, session.version)) {
    const items = [];
    for (const item of section.items) {
      const url = "href" in item ? item.href : links[item.key];
      if (!url) continue;
      const isActive = "key" in item && item.key === active;
      const badge = "key" in item && item.key === "extensions" ? extensionUpdates : 0;
      items.push(<ItemLink key={item.label} item={item} url={url} active={isActive} badge={badge} />);
    }
    if (items.length === 0) continue;
    sections.push(
      <div key={section.heading}>
        <div className="menu-item pt-5">
          <div className="menu-content">
            <span className="menu-heading fw-bold text-uppercase fs-7">{section.heading}</span>
          </div>
        </div>
        {items}
      </div>,
    );
  }

  const drawerClasses = drawer ? ` drawer drawer-start${open ? " drawer-on" : ""}` : "";
  return (
    <>
      <aside
        id="kt_app_sidebar"
        className={`app-sidebar flex-column${drawerClasses}`}
        aria-label={gettext("Sidebar")}
        aria-hidden={drawer && !open ? true : undefined}
      >
        <div className="app-sidebar-logo px-6" id="kt_app_sidebar_logo">
          <Link to="/" aria-label={session.branding.productName}>
            <img alt="" src={session.branding.logoUrl} className="h-25px app-sidebar-logo-default" />
          </Link>
        </div>
        {/*
          the menu takes the sidebar's height below the logo, and scrolls. Keen's own sidebar gets its height from
          Keen's JavaScript, which the console doesn't load: flex-grow-1 with overflow-hidden lets the menu shrink
          to what is left, and h-100 gives the scrolling wrapper that height.
        */}
        <div className="app-sidebar-menu overflow-hidden flex-grow-1">
          <nav className="app-sidebar-wrapper hover-scroll-overlay-y h-100 py-5" aria-label={gettext("Main")}>
            <div className="menu menu-column menu-rounded menu-sub-indention px-3 fw-semibold fs-6">{sections}</div>
          </nav>
        </div>
      </aside>
      {drawer && open && (
        <button
          type="button"
          className="drawer-overlay border-0 p-0"
          aria-label={gettext("Hide the sidebar")}
          onClick={onClose}
        />
      )}
    </>
  );
}
