/**
 * TabbedListView React Component
 *
 * Displays a tabbed interface for viewing objects owned by the current user
 * and objects shared with the user, one page at a time.
 *
 * Tabs:
 * - Your LLMClients
 * - Shared LLMClients
 *
 * The tabs are those of the tabbedListViewContext, whose keys are the slugs of the list api that
 * loads them, e.g. "owned" and "shared". A tab may also have its own ListView, DetailView and object
 * type name, e.g. the read-only Extensions tab of the LLMTool list, whose objects are not LLMTools.
 *
 * Each row of the list opens the resource's detail, ResourceDetail, when it is clicked, or when it has the focus
 * and Enter is pressed. A click on a row's links, buttons or chips does what they do instead. The detail's tabs are
 * the list's DetailView, the resource's manifest, the hierarchy of the resources that it uses, and the resources
 * that use it. Its Previous and Next buttons, and the arrow keys, browse the list from the detail, from one page to
 * the next. The detail closes when the tab, the search, the sort or what narrows the list changes.
 *
 * Features:
 * - Loads owned and shared llmclient lists from the backend using session context.
 * - Paginates each tab: previous and next page buttons, and a page number box. The backend
 *   paginates, so each page is a request to the list api, for ?page=N.
 * - Searches both tabs: the backend searches all of the objects, not only the page shown, so
 *   the search is a request to the list api, for ?search=..., once typing pauses. A new search
 *   returns each tab to its first page.
 * - Sorts both tabs by a column, when the list view's header of the column is clicked (see
 *   SortableHeader): the backend sorts all of the objects, not only the page shown, so a new sort
 *   is a request to the list api, for ?ordering=name or ?ordering=-name, and it returns each tab
 *   to its first page. The list api says which columns it can sort by.
 * - Narrows both tabs by a named filter of the list api, when the page is opened with
 *   ?filter=<name>, e.g. the dashboard's pending deployments link, ?filter=pending. A chip shows the
 *   filter's label, from the tabbedListViewContext's filters, and a button that removes it.
 * - Narrows both tabs by tags and by an annotation selector, ?tag=<name> and
 *   ?annotation=<requirement>, each repeatable: when the page is opened with them, e.g. from the
 *   dashboard's search, when a tag or annotation of an object is clicked (see Filtering), and when a
 *   requirement is typed in the annotation selector box. Each shows as a chip with a button that
 *   removes it, and the page's url follows them, so that it can be bookmarked or shared. The list
 *   api reports an invalid selector, which is shown under the box, and not applied.
 * - Opens searching, when the page is opened with ?search=<text>, which also follows the search.
 * - Shows a page from the cache at once, when it holds it, while the page is fetched again, with a
 *   small spinner that says it is refreshing.
 * - Shows loading and error states during fetches.
 * - Uses cookie-backed counts (owned/shared) to size loading skeleton rows.
 * - Supports requery with cache invalidation, from the Refresh button at the top of the list, and
 *   from the list and card views after a clone, rename or delete.
 *
 * Props:
 * - sessionContext (SessionContext): Authentication and API context used for requests.
 *
 * State:
 * - lists: Each tab's objects, loading state, and pagination, as the list api last described it.
 * - pages: Each tab's requested page.
 * - searchInput: The search as typed; search: the search requested, once typing pauses.
 * - ordering: The column that sorts both tabs, e.g. "name", or "-name" in descending order. Empty for the default order.
 * - errorMessage: Error text for failed requests.
 * - activeTab: Current tab, the key of one of the tabbedListViewContext's tabs, e.g. "owned".
 * - selection: The row whose detail is open, by its tab and index on the tab's page, or null. While the detail
 *   moves to another page, pending says whether it shows that page's first or last row, once it loads.
 *
 * Internal Helpers:
 * - getCookie: Reads cookie values used for skeleton sizing.
 * - load (from ./load): Fetches llmclient data and updates state via setters.
 *
 * Page Rendering Performance and Caching behavior:
 * - Improves the perceived load time by rendering cached results immediately when
 *   available while a fresh backend fetch is still in flight (stale-while-revalidate). The list
 *   api caches its pages too (smarter.lib.django.listview), so the fresh fetch is usually quick.
 * - Reads each page from localStorage, keyed by the session, the API URL, the tab, and the page's
 *   page number, ordering and filter, on mount and whenever the page, ordering or filter changes.
 * - Writes every successful fetch without a search back to the cache, with its pagination, so that
 *   a return visit, a new browser tab, or paging back shows recent data without waiting on the network.
 *
 * Usage:
 * <TabbedListView sessionContext={sessionContext} />
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent as ReactKeyboardEvent, MouseEvent as ReactMouseEvent } from "react";

import type {
  DetailViewBaseProps,
  Filtering,
  ListViewBaseProps,
  Pagination,
  SessionContext,
  Sorting,
  TabbedViewContext,
  TabKey,
} from "../../lib/Types";
import { load } from "../../lib/load";
import { loggerPrefix } from "../../lib/const";
import { makeCacheKey, readCache, sessionScope, writeCache } from "../../lib/cache";

import ResourceDetail from "../ResourceDetail";

import { getCookieForUrl } from "./cookie";
import { PaginationControls } from "./PaginationControls";
import { AnnotationSelectorBox } from "./AnnotationSelectorBox";
import { FilterChip } from "./FilterChip";
import { SearchBox } from "./SearchBox";
import { TabNav } from "./TabNavigation";
import { gettext, interpolate } from "../../lib/i18n";

type TabbedListViewProps<TObject> = {
  sessionContext: SessionContext;
  tabbedListViewContext: TabbedViewContext<TObject>;
};

// a tab's objects are of the list's object type, or of the tab's own (see Tab), so the tabbed
// list view holds them as unknown, and its views say what they are.
type TabList = {
  objects: unknown[];
  isLoading: boolean;
  /** Whether the objects shown are cached ones, while the list api is asked for fresh ones. */
  isRefreshing: boolean;
  pagination: Pagination | null;
};

type TabRecord<T> = Record<TabKey, T>;

/** A record with a value for each tab. */
function tabRecord<T>(tabKeys: TabKey[], value: (tab: TabKey) => T): TabRecord<T> {
  return Object.fromEntries(tabKeys.map((tab) => [tab, value(tab)])) as TabRecord<T>;
}

/** The named filter that the page's url asks for, e.g. "pending" for ?filter=pending, or "". */
function filterOfPageUrl(): string {
  return new URLSearchParams(window.location.search).get("filter")?.trim() ?? "";
}

/** The distinct, non-empty values of a repeated parameter of the page's url, e.g. ["a", "b"] for ?tag=a&tag=b. */
function valuesOfPageUrl(name: string): string[] {
  const values = new URLSearchParams(window.location.search).getAll(name).map((value) => value.trim());
  return values.filter((value, index) => value && values.indexOf(value) === index);
}

/** Make a parameter of the page's url these values, or remove it, without a new history entry. */
function setPageUrlValues(name: string, values: string[]): void {
  const url = new URL(window.location.href);
  url.searchParams.delete(name);
  values.forEach((value) => url.searchParams.append(name, value));
  if (url.href !== window.location.href) window.history.replaceState(window.history.state, "", url);
}

/** What narrows both tabs, besides the search: the named filter, tags, and an annotation selector. */
type Narrowing = {
  filter: string;
  tags: string[];
  annotations: string[];
};

/** The row whose detail is open: its tab, and its index on the tab's page. See TabbedListView's selection. */
type Selection = {
  tab: TabKey;
  index: number;
  /** After the detail moved to another page: whether it shows that page's first or last row, once it loads. */
  pending?: "first" | "last";
  /** What the list showed when the detail opened: its search, sort and narrowing. See TabbedListView's shown. */
  shown: string;
};

/**
 * What a click on a row does itself, rather than open the row's detail: its links, buttons, form fields, chips,
 * menus, and the dialogs that its Toolbar opens.
 */
const ROW_CONTROLS =
  "a, button, input, select, textarea, label, summary, [role='button'], [role='menu'], [role='menuitem'], [role='dialog'], .dropdown-menu";

/** The rows of a list view's table that are objects: not its loading skeleton's ghost rows. */
const OBJECT_ROWS = "tbody > tr:not(.ghost)";

/** How long to wait after the last keystroke of a search before it is requested, in milliseconds. */
export const SEARCH_DELAY_MS = 300;

// throttle duration for requerying to prevent excessive backend requests
const REQUERY_THROTTLE_MS = 2000;

export default function TabbedListView<TObject>({
  sessionContext,
  tabbedListViewContext,
}: TabbedListViewProps<TObject>) {
  const tabs = tabbedListViewContext.tabs;
  const tabKeys = useMemo(() => tabs.map((tab) => tab.key), [tabs]);

  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // list state management for owned/shared object lists.
  //
  // We'll be optimistic, and hope that cached data is available to populate
  // these before the async load completes. If not, then we'll show loading
  // skeletons until the load finishes and populates these states. Note that
  // the skeletons make use of cookie-backed counts to size themselves to whatever
  // they'd most recently been, which should help prevent jarring resizing when
  // the real data loads.
  // A list is loading until the first load completes, unless its cache already has its objects.
  // The cache holds every page, ordering and filter that the list showed, but no search, in
  // localStorage, scoped by the session, so that a list paints at once on a return visit, in a new
  // browser tab, and when paging back. See ../../lib/cache.
  // the named filter of both tabs, from the page's url.
  const [filter, setFilter] = useState(filterOfPageUrl);
  // the tags and annotation selector of both tabs, from the page's url, then from the chips and the selector box.
  const [tags, setTags] = useState(() => valuesOfPageUrl("tag"));
  const [annotations, setAnnotations] = useState(() => valuesOfPageUrl("annotation"));
  const narrowing = useMemo<Narrowing>(() => ({ filter, tags, annotations }), [filter, tags, annotations]);
  const scope = useMemo(() => sessionScope(sessionContext), [sessionContext]);
  const cacheKey = useCallback(
    (tab: TabKey, page: number, tabOrdering: string, tabNarrowing: Narrowing) =>
      makeCacheKey(sessionContext.ApiUrl, tab, { page, ordering: tabOrdering, ...tabNarrowing }, scope),
    [sessionContext, scope],
  );
  const [lists, setLists] = useState<TabRecord<TabList>>(() =>
    tabRecord(tabKeys, (tab) => {
      const cached = readCache<unknown>(cacheKey(tab, 1, "", narrowing));
      return {
        objects: cached?.objects ?? [],
        isLoading: cached === null,
        isRefreshing: cached !== null,
        pagination: cached?.pagination ?? null,
      };
    }),
  );

  // each tab's requested page, and the search of both tabs. searchInput is the search as it is
  // typed, and search follows it once typing pauses, so that every keystroke is not a request.
  const [pages, setPages] = useState<TabRecord<number>>(() => tabRecord(tabKeys, () => 1));
  const [searchInput, setSearchInput] = useState(() => new URLSearchParams(window.location.search).get("search") ?? "");
  const [search, setSearch] = useState(() => searchInput.trim());
  // the column that sorts both tabs, as the list api names it, e.g. "-name". Empty for its default order.
  const [ordering, setOrdering] = useState("");

  // only the latest request of a tab is shown, when several are in flight, e.g. when the user
  // pages quickly, or a requery and a page change overlap.
  const latestRequest = useRef<TabRecord<number>>(tabRecord(tabKeys, () => 0));

  // for sizing the skeleton loaders that are rendered if no cached data is available
  const maxGhostRows = 25;
  const clamp = (val: number, min: number, max: number) => Math.max(min, Math.min(max, val));
  const ghostCount = (tab: TabKey) => clamp(getCookieForUrl(sessionContext.ApiUrl + tab + "/") || 6, 0, maxGhostRows);

  const [activeTab, _setActiveTab] = useState<TabKey>(() => tabKeys[0]);
  const [selection, setSelection] = useState<Selection | null>(null);
  const setActiveTab = (tab: TabKey) => {
    setSelection(null);
    _setActiveTab(tab);
  };
  // the list view's table, whose rows open their details.
  const listRef = useRef<HTMLDivElement>(null);

  const requeryRef = useRef<number | null>(null);

  // load a page of a tab's objects that match the search, in the ordering.
  // invalidateCache: whether the backend (Django-Redis) cache should be invalidated, e.g. after a
  // clone, rename or delete. It is a parameter, rather than state, so that a requery's load sees it.
  // isActive: whether the results are still wanted; a load that a newer one replaced, or that
  // finishes after the component unmounts, is ignored.
  const loadTab = useCallback(
    (
      tab: TabKey,
      page: number,
      tabSearch: string,
      tabOrdering: string,
      tabNarrowing: Narrowing,
      invalidateCache: boolean,
      isActive: () => boolean = () => true,
    ): Promise<void> => {
      const request = (latestRequest.current[tab] ?? 0) + 1;
      latestRequest.current[tab] = request;
      // show the page from the cache at once, if it holds it, and its loading skeleton otherwise.
      const key = cacheKey(tab, page, tabOrdering, tabNarrowing);
      const cached = tabSearch ? null : readCache<unknown>(key);
      setLists((prev) => ({
        ...prev,
        [tab]: cached
          ? { objects: cached.objects, pagination: cached.pagination, isLoading: false, isRefreshing: true }
          : { ...prev[tab], isLoading: true, isRefreshing: false },
      }));
      console.debug(
        `${loggerPrefix} loadTab() Loading ${tab} objects, page=${page}, search="${tabSearch}", ordering="${tabOrdering}", narrowing=${JSON.stringify(tabNarrowing)}, invalidateCache=${invalidateCache}`,
      );
      return load<unknown>(sessionContext, invalidateCache, tab, setErrorMessage, {
        page,
        search: tabSearch,
        ordering: tabOrdering,
        ...tabNarrowing,
      }).then(({ objects, pagination }) => {
        if (!isActive() || request !== latestRequest.current[tab]) return;
        console.debug(`${loggerPrefix} loadTab() received ${tab} objects:`, objects, pagination);
        setLists((prev) => ({ ...prev, [tab]: { objects, isLoading: false, isRefreshing: false, pagination } }));
        if (!tabSearch && pagination) {
          writeCache(key, objects, pagination);
        }
      });
    },
    [sessionContext, cacheKey],
  );

  const onPage = (page: number) => {
    console.debug(`${loggerPrefix} onPage() going to page ${page} of the ${activeTab} objects`);
    setPages((prev) => ({ ...prev, [activeTab]: page }));
  };

  // sort both tabs by a column, from their first pages.
  const onSort = (requested: string) => {
    console.debug(`${loggerPrefix} onSort() sorting by "${requested}", reloading the first page of each tab`);
    setPages(tabRecord(tabKeys, () => 1));
    setOrdering(requested);
  };

  // show every object again: remove the filter, from the list and from the page's url.
  const clearFilter = () => {
    console.debug(
      `${loggerPrefix} clearFilter() removing the "${filter}" filter, reloading the first page of each tab`,
    );
    const url = new URL(window.location.href);
    url.searchParams.delete("filter");
    window.history.replaceState(window.history.state, "", url);
    setPages(tabRecord(tabKeys, () => 1));
    setFilter("");
  };

  // narrow both tabs by one more tag or annotation requirement, or by one fewer, from their first pages.
  const narrowBy = (name: "tag" | "annotation", values: string[], setValues: (values: string[]) => void) => {
    console.debug(`${loggerPrefix} narrowBy() ${name}=${JSON.stringify(values)}, reloading the first page of each tab`);
    setPageUrlValues(name, values);
    setPages(tabRecord(tabKeys, () => 1));
    setValues(values);
  };
  const addTag = (tag: string) => {
    if (tag && !tags.includes(tag)) narrowBy("tag", [...tags, tag], setTags);
  };
  const removeTag = (tag: string) =>
    narrowBy(
      "tag",
      tags.filter((item) => item !== tag),
      setTags,
    );
  const addAnnotation = (requirement: string) => {
    const trimmed = requirement.trim();
    if (trimmed && !annotations.includes(trimmed)) narrowBy("annotation", [...annotations, trimmed], setAnnotations);
  };
  const removeAnnotation = (requirement: string) =>
    narrowBy(
      "annotation",
      annotations.filter((item) => item !== requirement),
      setAnnotations,
    );
  const filtering: Filtering = { tags, annotations, onTag: addTag, onAnnotation: addAnnotation };

  // request the search once typing pauses, from the first page of each tab.
  useEffect(() => {
    const timer = setTimeout(() => {
      const requested = searchInput.trim();
      if (requested === search) return;
      console.debug(`${loggerPrefix} search changed to "${requested}", reloading the first page of each tab`);
      setPageUrlValues("search", requested ? [requested] : []);
      setPages(tabRecord(tabKeys, () => 1));
      setSearch(requested);
    }, SEARCH_DELAY_MS);
    return () => clearTimeout(timer);
  }, [searchInput, search, tabKeys]);

  const onRequery = () => {
    console.debug(`${loggerPrefix} onRequery() called, reloading data and invalidating the backend cache`);
    if (tabKeys.some((tab) => lists[tab]?.isLoading)) {
      return;
    }
    // throttle to prevent excessive requerying if user clicks multiple times in a short span
    const now = Date.now();
    if (requeryRef.current && now - requeryRef.current < REQUERY_THROTTLE_MS) {
      return;
    }
    requeryRef.current = now;
    tabKeys.forEach((tab) => void loadTab(tab, pages[tab], search, ordering, narrowing, true));
  };

  // whether the component is mounted: the results of a load that finishes after it unmounts are ignored.
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  // each tab's last requested page, search and ordering, and the loadTab that requested them, so
  // that a tab is loaded again only when its own request changes, or the session context does.
  const requested = useRef<{ loadTab: typeof loadTab | null; params: Partial<Record<TabKey, string>> }>({
    loadTab: null,
    params: {},
  });

  // load each tab on mount, whenever the session context changes, and whenever its page, the
  // search or the ordering changes. The cached objects, if any, are shown at once (see the state initializers
  // above), and replaced by the freshly loaded ones.
  useEffect(() => {
    if (requested.current.loadTab !== loadTab) {
      requested.current = { loadTab, params: {} };
    }
    tabKeys.forEach((tab) => {
      const page = pages[tab] ?? 1;
      const params = JSON.stringify([page, search, ordering, narrowing]);
      if (requested.current.params[tab] === params) return;
      requested.current.params[tab] = params;
      void loadTab(tab, page, search, ordering, narrowing, false, () => mounted.current);
    });
  }, [loadTab, tabKeys, pages, search, ordering, narrowing]);

  // the detail that is open. It closes when what the list shows changes: its search, its sort, or what narrows it.
  const shown = JSON.stringify([search, ordering, narrowing]);
  const current = selection && selection.shown === shown ? selection : null;
  const selectedList = current ? lists[current.tab] : null;
  // the detail that moved to another page shows the row that it left, until that page loads, and then that page's
  // first or last row. A detail whose row is gone, e.g. deleted from the detail, shows the page's last row, and
  // closes if the page has none.
  const pageLoaded =
    !!current &&
    !!selectedList &&
    !selectedList.isLoading &&
    (!selectedList.pagination || selectedList.pagination.page === (pages[current.tab] ?? 1));
  const isNavigating = !!current?.pending && !pageLoaded;
  const selectedIndex: number | null = (() => {
    if (!current || !selectedList) return null;
    const count = selectedList.objects.length;
    if (count === 0) return null;
    if (current.pending && pageLoaded) return current.pending === "last" ? count - 1 : 0;
    return Math.min(current.index, count - 1);
  })();

  // each row of the list view can have the focus, and the row whose detail is open stands out. The list view
  // renders its rows a few at a time, so this follows its table as it changes.
  const highlighted = current?.tab === activeTab && !isNavigating ? selectedIndex : null;
  useEffect(() => {
    const container = listRef.current;
    if (!container) return;
    const sync = () => {
      container.querySelectorAll<HTMLTableRowElement>(OBJECT_ROWS).forEach((row, index) => {
        if (!row.hasAttribute("tabindex")) row.tabIndex = 0;
        row.classList.toggle("smarter-row-selected", index === highlighted);
      });
    };
    sync();
    const observer = new MutationObserver(sync);
    observer.observe(container, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [highlighted, activeTab]);

  if (errorMessage) {
    return (
      <div className="alert alert-danger" role="alert">
        {errorMessage}
      </div>
    );
  }

  const tab = tabs.find((item) => item.key === activeTab) ?? tabs[0];
  const list = lists[tab.key];
  const ghostRows = ghostCount(tab.key);
  // the active tab's views: its own, or the list's. A tab's objects are those that its views show.
  const listViewOf = (key: TabKey) => tabs.find((item) => item.key === key)?.ListView ?? tabbedListViewContext.ListView;
  const ListView = listViewOf(tab.key) as React.ComponentType<ListViewBaseProps<unknown, SessionContext>>;
  const objectTypeName = tab.objectTypeName ?? tabbedListViewContext.objectTypeName;
  // the columns that the list api can sort by. The response of any tab with the same list view
  // says, so that the headers of a tab are sortable even before its own first response.
  const sameView = tabKeys.filter((key) => listViewOf(key) === listViewOf(tab.key));
  const pagination = list.pagination ?? sameView.map((key) => lists[key].pagination).find(Boolean);
  const sortFields = pagination?.sortFields ?? [];
  const sorting: Sorting = { ordering, sortFields, onSort };
  // the filter that applies: the api ignores, and reports as "", a filter that it doesn't offer.
  const appliedFilter = list.pagination ? (list.pagination.filter ?? filter) : filter;
  const filterLabel = tabbedListViewContext.filters?.[appliedFilter] ?? appliedFilter;
  const annotationError = list.pagination?.annotationError ?? "";

  /** The index of the row of the list view's table that an event happened in, or null for a row's own controls. */
  const rowIndexOf = (target: EventTarget | null): number | null => {
    if (!(target instanceof Element) || target.closest(ROW_CONTROLS)) return null;
    const row = target.closest("tr");
    if (!row || !listRef.current?.contains(row)) return null;
    const index = Array.from(listRef.current.querySelectorAll(OBJECT_ROWS)).indexOf(row);
    return index >= 0 && index < list.objects.length ? index : null;
  };
  const openRow = (index: number | null) => {
    if (index === null) return;
    console.debug(`${loggerPrefix} openRow() opening the detail of row ${index} of the ${tab.key} objects`);
    setSelection({ tab: tab.key, index, shown });
  };
  const onRowClick = (e: ReactMouseEvent<HTMLDivElement>) => {
    // a click that ends a selection of the row's text leaves the text selected, so that it can be copied.
    if (window.getSelection()?.toString()) return;
    openRow(rowIndexOf(e.target));
  };
  const onRowKeyDown = (e: ReactKeyboardEvent<HTMLDivElement>) => {
    if ((e.key !== "Enter" && e.key !== " ") || !(e.target instanceof HTMLTableRowElement)) return;
    const index = rowIndexOf(e.target);
    if (index === null) return;
    e.preventDefault();
    openRow(index);
  };

  // the detail that is open, and how it browses the list: within the page, and on to the previous or next page.
  const detail = (() => {
    if (!current || !selectedList || selectedIndex === null) return null;
    const objects = selectedList.objects;
    const index = selectedIndex;
    const object = objects[index];
    const selectedTab = tabs.find((item) => item.key === current.tab) ?? tab;
    const page = pages[current.tab] ?? 1;
    const tabPagination = selectedList.pagination;
    const numPages = tabPagination?.numPages ?? 1;
    const goTo = (next: Omit<Selection, "shown">) => {
      if (next.pending) {
        setPages((prev) => ({ ...prev, [next.tab]: page + (next.pending === "first" ? 1 : -1) }));
      }
      setSelection({ ...next, shown });
    };
    const onPrevious =
      index > 0
        ? () => goTo({ tab: current.tab, index: index - 1 })
        : page > 1
          ? () => goTo({ tab: current.tab, index: 0, pending: "last" })
          : undefined;
    const onNext =
      index < objects.length - 1
        ? () => goTo({ tab: current.tab, index: index + 1 })
        : page < numPages
          ? () => goTo({ tab: current.tab, index: 0, pending: "first" })
          : undefined;
    const position = tabPagination
      ? { index: (tabPagination.page - 1) * tabPagination.pageSize + index + 1, count: tabPagination.count }
      : { index: index + 1, count: objects.length };
    return (
      <ResourceDetail
        sessionContext={sessionContext}
        object={object}
        objectTypeName={selectedTab.objectTypeName ?? tabbedListViewContext.objectTypeName}
        DetailView={
          (selectedTab.DetailView ?? tabbedListViewContext.DetailView) as React.ComponentType<
            DetailViewBaseProps<unknown, SessionContext>
          >
        }
        onRequery={onRequery}
        filtering={filtering}
        position={position}
        onPrevious={onPrevious}
        onNext={onNext}
        isNavigating={isNavigating}
        onClose={() => setSelection(null)}
      />
    );
  })();

  return (
    <div className="pt-5 pb-5 card card-flush h-xl-100">
      <div className="card-header rounded align-items-start ps-3" data-bs-theme="light">
        <TabNav activeTab={tab.key} onTabChange={setActiveTab} tabs={tabs} />
      </div>
      <div className="m-0 p-0 card-body list-view">
        <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 pe-3">
          <div className="d-flex flex-wrap align-items-center gap-3 ps-3">
            {list.isRefreshing && (
              <span
                className="spinner-border spinner-border-sm text-primary opacity-75"
                role="status"
                title={gettext("Refreshing")}
                aria-label={gettext("Refreshing")}
              ></span>
            )}
            {appliedFilter && (
              <FilterChip
                // Translators: the label of the filter that narrows a list, e.g. "Pending deployment".
                label={interpolate(gettext("Showing: %(filter)s"), { filter: filterLabel })}
                removeLabel={gettext("Show all")}
                onRemove={clearFilter}
              />
            )}
            {tags.map((tag) => (
              <FilterChip
                key={`tag:${tag}`}
                // Translators: tag is a resource's tag, e.g. production.
                label={interpolate(gettext("Tag: %(tag)s"), { tag })}
                onRemove={() => removeTag(tag)}
              />
            ))}
            {annotations.map((requirement) => (
              <FilterChip
                key={`annotation:${requirement}`}
                // Translators: requirement is an annotation selector's requirement, e.g. acme.com/crm-id=A-1.
                label={interpolate(gettext("Annotation: %(requirement)s"), { requirement })}
                onRemove={() => removeAnnotation(requirement)}
              />
            ))}
          </div>
          <div className="d-flex flex-wrap align-items-start gap-3">
            <AnnotationSelectorBox onAdd={addAnnotation} error={annotationError} />
            <SearchBox
              value={searchInput}
              onChange={setSearchInput}
              placeholder={
                // Translators: objects is the plural of a resource kind's name, e.g. secrets.
                interpolate(gettext("Search %(objects)s"), { objects: `${objectTypeName}s` })
              }
            />
            <button
              type="button"
              className="btn btn-sm btn-light"
              disabled={list.isLoading || list.isRefreshing}
              title={gettext("Load the list again, with the latest changes")}
              onClick={onRequery}
            >
              <i className="ki-outline ki-arrows-circle fs-4 me-1" aria-hidden="true" />
              {gettext("Refresh")}
            </button>
          </div>
        </div>

        {/* a row opens its detail, when it is clicked, or when it has the focus and Enter is pressed. Each row
            is focusable (see above), so the keyboard reaches it, and its own controls keep their behavior. */}
        {/* eslint-disable-next-line jsx-a11y/no-static-element-interactions */}
        <div ref={listRef} className="smarter-selectable-rows" onClick={onRowClick} onKeyDown={onRowKeyDown}>
          <ListView
            key={tab.key}
            isLoading={list.isLoading}
            ghostRows={ghostRows}
            sessionContext={sessionContext}
            objects={list.objects}
            onRequery={onRequery}
            sorting={sorting}
            filtering={filtering}
          />
        </div>

        {list.pagination && list.pagination.count > 0 && (
          <PaginationControls pagination={list.pagination} disabled={list.isLoading} onPage={onPage} />
        )}
      </div>
      {detail}
    </div>
  );
}
