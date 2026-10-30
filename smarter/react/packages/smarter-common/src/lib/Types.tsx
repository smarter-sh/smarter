/**
 * Central type definitions for the Prompt List React application.
 *
 * This module exports TypeScript types and interfaces used throughout the DetailView,
 * llmclient, and API response layers. It provides strong typing for user, plugin,
 * llmclient, API response, and session context data structures.
 *
 * Exports:
 *   - TabKey: Type for tab keys ("owned", "shared", or another slug of the list api).
 *   - Tab, Tabs: A TabbedListView's tabs, each of which may have its own object type and views.
 *   - Pagination, ListQuery, ListPage: Types for a page of a list api, and the request for it.
 *   - Sorting: The sort of a list view's columns, which the list api sorts by.
 *   - Filtering: How a list view narrows its list by a tag or annotation that is clicked.
 *   - Plugin: Type for plugin objects.
 *   - User, UserProfile: Types for user and profile data.
 *   - LLMClient: Type for llmclient configuration and metadata.
 *   - SessionContext: Type for session and authentication context.
 *
 * Usage:
 *   Import these types to ensure type safety and consistency across components and API calls.
 */

/**
 * The key of a TabbedListView's tab, which is also the slug of the list api that loads it:
 * <ApiUrl><key>/. Most lists have the two ownership tabs, "owned" and "shared". A list may add
 * others, e.g. the LLMTool list's "extensions".
 */
export type TabKey = "owned" | "shared" | (string & {});

/** The description of a page of a list api's objects, as smarter.lib.django.pagination returns it. */
export type Pagination = {
  page: number;
  pageSize: number;
  numPages: number;
  count: number;
  search: string;
  /** The column that sorts the objects, e.g. "name", or "-name" in descending order. Empty for the api's default order. */
  ordering: string;
  /** The columns that the list api can sort by. */
  sortFields: string[];
  /** The named filter that narrows the objects, e.g. "pending", or empty for none. */
  filter?: string;
  /** The named filters that the list api offers. */
  filters?: string[];
  /** The tags that every object has, e.g. ["production"]. */
  tags?: string[];
  /** The annotation selector's requirements that every object matches, e.g. ["acme.com/crm-id=A-1"]. */
  annotations?: string[];
  /** Why the annotation selector is invalid, in which case the list api didn't apply it, or empty. */
  annotationError?: string;
};

/** The page of a list api's objects to request, the search and named filter that they match, and their order. All are optional. */
export type ListQuery = {
  page?: number;
  pageSize?: number;
  search?: string;
  ordering?: string;
  filter?: string;
  /** Tags that every object must have. */
  tags?: string[];
  /** An annotation selector's requirements, e.g. "acme.com/crm-id=A-1" or "!acme.com/archived". */
  annotations?: string[];
};

/**
 * How a list view narrows its list by an object's tag or annotation, when one is clicked. The list
 * api filters all of the objects, not only those of the page shown, so TabbedListView requests them.
 *
 * - tags, annotations: the tags and annotation requirements that narrow the list now.
 * - onTag: narrows the list to the objects with a tag.
 * - onAnnotation: narrows the list by an annotation requirement, e.g. "acme.com/crm-id=A-1".
 */
export type Filtering = {
  tags: string[];
  annotations: string[];
  onTag: (tag: string) => void;
  onAnnotation: (requirement: string) => void;
};

/**
 * The sort of a list view's columns. The list api sorts all of the objects, not only those of the
 * page shown, so a new sort is a request to the list api, which TabbedListView makes.
 *
 * - ordering: the column that sorts the objects, e.g. "name", or "-name" in descending order. Empty for the default order.
 * - sortFields: the columns that the list api can sort by. Other columns are not sortable.
 * - onSort: requests another ordering.
 */
export type Sorting = {
  ordering: string;
  sortFields: string[];
  onSort: (ordering: string) => void;
};

/** A page of a list api's objects. pagination is null when the api does not describe its pages. */
export type ListPage<TObject> = {
  objects: TObject[];
  pagination: Pagination | null;
};

/** A resource's annotations, as in Kubernetes: a map of keys to string values. */
export type Annotations = Record<string, string> | null;
export type Tags = string[] | null;

export type User = {
  username: string;
  email: string;
};
export type UserProfile = {
  user: User;
  account?: {
    accountNumber: string;
  };
};

export type ListViewBaseProps<TObject, TSessionContext> = {
  isLoading: boolean;
  ghostRows: number;
  sessionContext: TSessionContext;
  objects: TObject[];
  onRequery: () => void;
  sorting?: Sorting;
  filtering?: Filtering;
};

/**
 * The props of a list's DetailView: the Details tab of the resource detail that opens when a row of the list is
 * chosen. It shows one object, with the building blocks of components/ResourceDetail (DetailSection, DetailField,
 * ResourceMetadataSection).
 */
export type DetailViewBaseProps<TObject, TSessionContext> = {
  sessionContext: TSessionContext;
  object: TObject;
  onRequery: () => void;
  filtering?: Filtering;
};

/**
 * The fields of a list's object that its resource detail reads, besides those that its DetailView shows. Every list
 * api's serializer sends them (smarter.apps.account.serializers.MetaDataWithOwnershipModelSerializer).
 *
 * - name: the title of the detail. An object without a name, e.g. an Extension, is called by its display name,
 *   title or slug.
 * - detailUrl: the url of the detail's Manifest, Hierarchy and Dependencies tabs. A row without one, e.g. an
 *   Extension's, has only the Details tab.
 */
export type DetailObject = {
  id?: number | string;
  name?: string | null;
  displayName?: string | null;
  title?: string | null;
  slug?: string | null;
  detailUrl?: string | null;
};

export type SessionContext = {
  ApiUrl: string;
  csrfCookieName: string;
  djangoSessionCookieName: string;
  cookieDomain: string;
  debugMode: boolean;
  smarterClient: string;
  smarterClientVersion: string;
  smarterRequestId: string;
  smarterCapabilities?: string[];
};

/**
 * A tab of a TabbedListView. A tab whose objects are of another type than the list's, e.g. the
 * read-only Extensions tab of the LLMTool list, supplies its own ListView, DetailView, and the name
 * of its object type, for the search box. Its ListView and DetailView are typed with `never`
 * objects, so that a component of any object type may be given.
 */
export type Tab = {
  key: TabKey;
  label: string;
  objectTypeName?: string;
  ListView?: React.ComponentType<ListViewBaseProps<never, SessionContext>>;
  DetailView?: React.ComponentType<DetailViewBaseProps<never, SessionContext>>;
};

export type Tabs = Tab[];

export type TabbedViewContext<TObject> = {
  objectType: TObject;
  objectTypeName: string;
  tabs: Tabs;
  /**
   * The labels of the list api's named filters, by name, e.g. { pending: "Pending deployment" }.
   * A page opened with ?filter=<name> is narrowed by that filter, and shows its label.
   */
  filters?: Record<string, string>;
  ListView: React.ComponentType<ListViewBaseProps<TObject, SessionContext>>;
  /** The Details tab of the resource detail that opens when a row of the list is chosen. */
  DetailView: React.ComponentType<DetailViewBaseProps<TObject, SessionContext>>;
};
