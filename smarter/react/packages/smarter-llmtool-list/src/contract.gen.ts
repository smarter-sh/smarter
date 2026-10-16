/**
 * The LLMTool list's Extensions tab api contract: generated from contract/extension-list.schema.json by
 * scripts/contract-types.mjs. Do not edit; run `npm run contract:types`.
 */

/**
 * The responses of the read-only Extensions tab of the web console's LLMTool list. Generated from smarter.apps.llmtool.views.listview.contract; do not edit.
 */
export interface SmarterLLMToolListExtensionsApiContract {
  [k: string]: unknown;
}
/**
 * An installed Extension, as the read-only Extensions tab of the LLMTool list shows it.
 *
 * This interface was referenced by `SmarterLLMToolListExtensionsApiContract`'s JSON-Schema
 * via the `definition` "ExtensionListItem".
 */
export interface ExtensionListItem {
  createdAt: string;
  description: string;
  displayName: string;
  /**
   * Whether the extension's tools are offered to LLMs.
   */
  enabled: boolean;
  /**
   * The homepage, from the installed version's manifest.
   */
  homepage: string | null;
  id: number;
  /**
   * The license, from the installed version's manifest.
   */
  license: string | null;
  /**
   * The publisher's registry id, or an uploaded archive's authors.
   */
  publisher: string;
  /**
   * The extension's slug, e.g. weather. An LLMClient manifest lists it by slug.
   */
  slug: string;
  source: "registry" | "upload";
  trustBadge: "official" | "verified" | "community" | "unverified";
  /**
   * The badge, as people read it, e.g. Official Smarter Extension.
   */
  trustBadgeLabel: string;
  updatedAt: string;
  /**
   * The installed version.
   */
  version: string | null;
}
/**
 * A page of the Extensions tab: the extensions, and the description of the page.
 *
 * This interface was referenced by `SmarterLLMToolListExtensionsApiContract`'s JSON-Schema
 * via the `definition` "ExtensionListPage".
 */
export interface ExtensionListPage {
  objects: ExtensionListItem[];
  pagination: ListViewPagination;
}
/**
 * The description of one page of a list api's resources, as :func:`paginate_listview` returns it.
 *
 * Its JSON is camelCase, e.g. ``pageSize``.
 *
 * This interface was referenced by `SmarterLLMToolListExtensionsApiContract`'s JSON-Schema
 * via the `definition` "ListViewPagination".
 */
export interface ListViewPagination {
  /**
   * The number of resources that match the search, on every page.
   */
  count: number;
  /**
   * The number of pages.
   */
  numPages: number;
  /**
   * The column that sorts the list, e.g. -createdAt, or an empty string for the default order.
   */
  ordering?: string;
  /**
   * The page's number, from 1.
   */
  page: number;
  /**
   * The most resources that a page has.
   */
  pageSize: number;
  /**
   * The search, or an empty string.
   */
  search?: string;
  /**
   * The columns that the list may be sorted by.
   */
  sortFields?: string[];
}
