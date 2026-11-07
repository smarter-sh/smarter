/**
 * The sidebar's sections and items. The backend sends each item's url in the session's sidebar, or null when
 * the platform or the user doesn't have it (smarter.apps.api.web.session.views.sidebar); the console decides
 * the order, the labels and the icons.
 */
import { gettext, interpolate } from "@smarter/common";

import type { ConsoleBranding, ConsoleSidebar } from "@/contract.gen";
import { DASHBOARD_PATH, EXTENSIONS_PATH } from "@/lib/const";
import { JSON_SCHEMAS_PATH, MANIFESTS_PATH, OPENAPI_PATH } from "@/lib/docs";
import { DROPZONE_PATH, PASSTHROUGH_PATH, TERMINAL_PATH } from "@/lib/tools";
import { LIST_PAGES } from "@/lib/lists";

/**
 * The paths of the console's pages that the sidebar opens in place. Any other link, e.g. Django admin, loads the
 * backend's page.
 */
export const CONSOLE_PAGE_PATHS = [
  DASHBOARD_PATH,
  EXTENSIONS_PATH,
  DROPZONE_PATH,
  PASSTHROUGH_PATH,
  TERMINAL_PATH,
  MANIFESTS_PATH,
  JSON_SCHEMAS_PATH,
  OPENAPI_PATH,
  ...LIST_PAGES.map((page) => page.path),
];

/** The project's change log, which the Documentation section links to. */
export const CHANGELOG_URL = "https://github.com/smarter-sh/smarter/blob/main/changelogs/CHANGELOG.md";

interface SidebarItemBase {
  label: string;
  /** A Keenicons outline icon, e.g. "ki-category". */
  icon: string;
  /** The onboarding hint that points at it, if any. See @smarter/onboarding. */
  onboarding?: string;
}

/** A page of the platform, by the name of its url in the session's sidebar. */
export interface SidebarPageItem extends SidebarItemBase {
  key: keyof ConsoleSidebar;
}

/** A page elsewhere, which opens in a new tab. */
export interface SidebarExternalItem extends SidebarItemBase {
  href: string;
}

export type SidebarItem = SidebarPageItem | SidebarExternalItem;

export interface SidebarSection {
  heading: string;
  items: SidebarItem[];
}

/**
 * The sections, in order. A function, rather than a constant, so that the labels are translated when the
 * sidebar renders.
 *
 * @param branding - The platform's branding, for the documentation's links.
 * @param version - The platform's version, which the change log's label names.
 */
export function sidebarSections(branding: ConsoleBranding, version: string): SidebarSection[] {
  return [
    {
      heading: gettext("Workbench"),
      items: [
        { key: "dashboard", label: gettext("Dashboard"), icon: "ki-category" },
        { key: "promptPassthrough", label: gettext("Prompt Passthrough"), icon: "ki-code" },
        { key: "manifestDropZone", label: gettext("Apply Manifest"), icon: "ki-gear" },
        { key: "terminal", label: gettext("Terminal"), icon: "ki-screen" },
      ],
    },
    {
      heading: gettext("Models"),
      items: [
        { key: "providers", label: gettext("Providers"), icon: "ki-shop" },
        { key: "proxies", label: gettext("Proxies"), icon: "ki-data" },
        { key: "llmhost", label: gettext("LLM Hosts"), icon: "ki-message-programming" },
        { key: "llmhostcompute", label: gettext("LLM Host Compute"), icon: "ki-technology-2" },
      ],
    },
    {
      heading: gettext("Harnesses"),
      items: [
        {
          key: "workbench",
          label: gettext("LLM Clients"),
          icon: "ki-message-programming",
          onboarding: "sidebar-llmclients",
        },
        { key: "orchestrators", label: gettext("Orchestrators"), icon: "ki-message-programming" },
        { key: "apiKeys", label: gettext("API Keys"), icon: "ki-key" },
        { key: "customDomains", label: gettext("Custom Domains"), icon: "ki-arrow-circle-right" },
      ],
    },
    {
      heading: gettext("Tools"),
      items: [
        { key: "extensions", label: gettext("Extensions"), icon: "ki-element-plus" },
        { key: "plugins", label: gettext("LLM Tools"), icon: "ki-cube-2" },
        { key: "mcpclients", label: gettext("MCP Clients"), icon: "ki-message-programming" },
        { key: "connections", label: gettext("Connections"), icon: "ki-password-check" },
      ],
    },
    {
      heading: gettext("RAG"),
      items: [
        { key: "vectorsearches", label: gettext("Vectorsearches"), icon: "ki-data" },
        { key: "vectorstores", label: gettext("Vectorstores"), icon: "ki-data" },
      ],
    },
    {
      heading: gettext("Governance"),
      items: [
        { key: "budgets", label: gettext("Budgets"), icon: "ki-dollar" },
        { key: "guardrails", label: gettext("Guardrails"), icon: "ki-check" },
        { key: "secrets", label: gettext("Secrets"), icon: "ki-lock" },
      ],
    },
    {
      heading: gettext("Documentation"),
      items: [
        { href: branding.projectDocsUrl, label: gettext("Read the Docs"), icon: "ki-book-open" },
        { href: branding.projectWebsiteUrl, label: gettext("Project Web Site"), icon: "ki-abstract-14" },
        { key: "exampleManifests", label: gettext("Example Manifests"), icon: "ki-document" },
        { key: "openapi", label: gettext("OpenAPI Contract"), icon: "ki-document" },
        { key: "jsonSchemas", label: gettext("Json Schemas"), icon: "ki-document" },
        {
          href: CHANGELOG_URL,
          label: interpolate(gettext("GitHub Change Log %(version)s"), { version }),
          icon: "ki-github",
        },
      ],
    },
    {
      heading: gettext("Settings"),
      items: [
        { key: "infrastructureResources", label: gettext("Infrastructure Resources"), icon: "ki-cloud" },
        { key: "admin", label: gettext("Django Admin"), icon: "ki-setting-2" },
      ],
    },
  ];
}

/**
 * The item of a page: the one whose url is the longest that begins the page's path, so that a resource's own
 * pages, e.g. /secret/secrets/rMTAwx/, show under their list's item, /secret/.
 *
 * @param path - The page's path.
 * @param sidebar - The session's sidebar.
 * @returns The item's key, or null for a page of no item.
 */
export function activeSidebarItem(path: string, sidebar: ConsoleSidebar): keyof ConsoleSidebar | null {
  let active: keyof ConsoleSidebar | null = null;
  let longest = 0;
  // the backend's urls end with a slash, and the console's routes don't: /dashboard is /dashboard/'s page.
  const page = path.endsWith("/") ? path : `${path}/`;
  for (const [key, url] of Object.entries(sidebar) as [keyof ConsoleSidebar, string | null][]) {
    if (!url || !page.startsWith(url) || url.length <= longest) continue;
    active = key;
    longest = url.length;
  }
  return active;
}

/**
 * A backend url's path in the console: the backend's urls end with a slash, the console's routes don't.
 *
 * @param url - A link's url, e.g. /dashboard/.
 * @returns Its path without the trailing slash, e.g. /dashboard.
 */
export function consolePath(url: string): string {
  if (url.length > 1 && url.endsWith("/")) return url.slice(0, -1);
  return url;
}

/**
 * Whether a link's page has moved into the console, so that it opens in place.
 *
 * @param url - The link's url, as the session's sidebar has it.
 * @returns True for one of CONSOLE_PAGE_PATHS.
 */
export function isConsolePage(url: string): boolean {
  return CONSOLE_PAGE_PATHS.includes(consolePath(url));
}
