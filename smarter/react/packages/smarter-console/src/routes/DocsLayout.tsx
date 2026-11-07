/**
 * The frame of the docs pages, which are public: a header with the docs' links, the theme mode menu and a link into
 * the console (or to sign in), the page, and a footer. A page that has room for it shows the project's tools beside
 * its content (DocsArticle). It follows the theme's variables and utility classes, as the console's own frame does.
 */
import { gettext } from "@smarter/common";
import type { ReactNode } from "react";
import { Link, NavLink, Outlet } from "react-router";

import { ThemeModeMenu } from "@/components/ThemeModeMenu";
import { DASHBOARD_PATH, LOGIN_PATH } from "@/lib/const";
import { DOCS_TOOLS, JSON_SCHEMAS_PATH, MANIFESTS_PATH, OPENAPI_PATH } from "@/lib/docs";
import { useConsoleSession } from "@/session/context";

/** A link of the header, which shows when its page is open. */
function DocsNavLink({ to, children }: { to: string; children: ReactNode }) {
  return (
    <li className="nav-item">
      <NavLink
        to={to}
        className={({ isActive }) => `nav-link px-3 ${isActive ? "active fw-bold text-primary" : "text-gray-700"}`}
      >
        {children}
      </NavLink>
    </li>
  );
}

export function DocsLayout() {
  const { session } = useConsoleSession();
  if (!session) return null;
  const { branding } = session;

  return (
    <div className="d-flex flex-column min-vh-100 bg-body">
      <header className="border-bottom">
        <div className="container-xxl d-flex flex-wrap align-items-center justify-content-between gap-3 py-3">
          <Link to={MANIFESTS_PATH} aria-label={branding.productName}>
            <img alt="" src={branding.logoUrl} className="h-30px" />
          </Link>
          <nav aria-label={gettext("Documentation")}>
            <ul className="nav align-items-center">
              <DocsNavLink to={MANIFESTS_PATH}>{gettext("Manifests")}</DocsNavLink>
              <DocsNavLink to={JSON_SCHEMAS_PATH}>{gettext("JSON Schemas")}</DocsNavLink>
              <DocsNavLink to={OPENAPI_PATH}>{gettext("OpenAPI Contract")}</DocsNavLink>
              <li className="nav-item ms-2">
                {session.isAuthenticated ? (
                  <Link to={DASHBOARD_PATH} className="btn btn-sm btn-primary">
                    {gettext("Dashboard")}
                  </Link>
                ) : (
                  <Link to={LOGIN_PATH} className="btn btn-sm btn-primary">
                    {gettext("Sign In")}
                  </Link>
                )}
              </li>
              <li className="nav-item ms-2">
                <ThemeModeMenu />
              </li>
            </ul>
          </nav>
        </div>
      </header>
      <main className="container-xxl flex-grow-1 py-8">
        <Outlet />
      </main>
      <footer className="border-top">
        <div className="container-xxl d-flex flex-wrap justify-content-between gap-3 py-4 text-gray-600 fs-7">
          <span>{branding.copyright}</span>
          <span className="d-flex gap-4">
            <a href={branding.projectDocsUrl} className="text-gray-600 text-hover-primary">
              {gettext("Read the Docs")}
            </a>
            <a href={DOCS_TOOLS.github} className="text-gray-600 text-hover-primary">
              GitHub
            </a>
          </span>
        </div>
      </footer>
    </div>
  );
}

/** The project's tools for manifests, beside a page's content. */
function DocsTools() {
  const tools = [
    { href: DOCS_TOOLS.cli, label: gettext("Smarter CLI"), icon: "ki-code" },
    { href: DOCS_TOOLS.vscode, label: gettext("VS Code Extension"), icon: "ki-document" },
    { href: DOCS_TOOLS.npm, label: gettext("npm React Chat Component"), icon: "ki-message-text" },
    { href: DOCS_TOOLS.pypi, label: gettext("Python SDK on PyPI"), icon: "ki-package" },
  ];
  return (
    <aside className="card" aria-labelledby="docs-tools-heading">
      <div className="card-body">
        <h2 id="docs-tools-heading" className="fs-5 fw-bold mb-4">
          {gettext("Tools")}
        </h2>
        <ul className="list-unstyled mb-0">
          {tools.map((tool) => (
            <li key={tool.href} className="mb-3">
              <a href={tool.href} className="d-flex align-items-center gap-2 text-gray-800 text-hover-primary">
                <i className={`ki-outline ${tool.icon} fs-3`} aria-hidden="true" />
                {tool.label}
              </a>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}

/** A docs page's content, in a card, with the project's tools beside it from the xl breakpoint up. */
export function DocsArticle({ children }: { children: ReactNode }) {
  return (
    <div className="row g-8">
      <article className="col-xl-9">
        <div className="card">
          <div className="card-body p-lg-10">{children}</div>
        </div>
      </article>
      <div className="col-xl-3">
        <DocsTools />
      </div>
    </div>
  );
}
