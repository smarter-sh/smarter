List API Caching
================

Every resource list in the web console, e.g. the LLMClient, Secret or Guardrail list, is a React
app that asks its Django list api for one page of resources at a time (see :doc:`pagination`).
Each list api is a subclass of :class:`~smarter.lib.django.listview.SmarterListApiView`, which
declares the resource's model and serializer, the columns that sort it, and the relations that
its serializer reads. The base class does the rest: it filters the resources by ownership, joins
their owners and prefetches their tags and the declared relations, so that a page costs a few
queries however many resources it holds, and it caches the page.

Two caches, one request
-----------------------

A list is cached twice: in the browser, by the React list, and on the server, by its list api.
When a user opens a list, pages it, sorts it or comes back to it:

1. **The React list paints at once, from the browser's cache**, if it holds that page, with a small
   *Refreshing* spinner beside the view toggle. Otherwise it shows its loading skeleton.
2. **It asks the list api for the page anyway** (stale-while-revalidate), and replaces what it
   painted with the response, which it writes back to the browser's cache.
3. **The list api answers from Redis**, if it holds the page for that user, and builds it from the
   database otherwise, in a few queries, then caches it.

So a list that the user has seen before paints without waiting for the network, and the request
that refreshes it is usually a cache hit too.

The browser cache
-----------------

The React side is shared by every list, in the ``@smarter/common`` package
(``smarter/react/packages/smarter-common``):

- ``src/lib/cache.tsx`` stores pages in the browser's ``localStorage``, which outlives the browser
  tab, so a new tab or a return visit paints at once. ``makeCacheKey()`` names a page by the list
  api's url, the tab (``owned`` or ``shared``), and the page's number, ordering and filter. Searches
  are never cached. Each entry holds the page's objects and its ``pagination``, so the pagination
  controls paint with it.
- ``sessionScope()`` adds a hash of the session's CSRF cookie to every key. Django rotates the CSRF
  token at every login, so a page cached for one user is never shown to the next user of the same
  browser, and the token itself is never stored.
- ``readCache()`` and ``writeCache()`` treat a private window, blocked site data or a full quota as a
  cache miss, never an error. ``pruneCache()`` runs on each write: it removes entries older than a
  week, and keeps only the most recent hundred.
- ``TabbedListView`` (``src/components/TabbedListView``), the tabs, toolbar and pagination of every
  list, reads the cache whenever a tab's page, ordering or filter changes, and marks the tab
  ``isRefreshing`` while it shows a cached page. Its Refresh button asks the api for a fresh page
  with ``?invalidate_cache=true``, which also makes the user's cached pages on the server stale.

The server cache
----------------

The list api caches each page's whole response in Redis, with
:func:`~smarter.lib.cache.cache_results`, in
:func:`~smarter.lib.django.listview.cached_listview_page`. Its key is everything that can change the
page: the user, the ownership tab, the page, page size, search, ordering and filter, and the
generations described below. A page that is in the cache costs no query beyond the request's
session. On a miss, :meth:`~smarter.lib.django.listview.SmarterListApiView.build_page` builds it with
the relations that the list api declared, and its ``can_delete`` column asks once per page which
rows the user owns, rather than once per row.

Staying correct
---------------

A cached page is never stale for long, because its cache key includes three *generations*, values
that change whenever they are invalidated (:func:`~smarter.lib.django.listview.listview_cache_generation`):

- **the list's generation**, which changes whenever a resource that the list shows is saved or
  deleted. Each app connects its list to the models it shows, in its ``receivers.py``, with
  :func:`~smarter.lib.django.listview.connect_listview_cache`: the resource, the rows that its
  serializer nests, and the rows that decide whether it can be deleted, e.g. an LLMClient's
  plugins. Because ``receivers.py`` is imported by the app's ``AppConfig.ready()``, the Celery
  workers invalidate lists too;
- **the user's generation of the list**, which changes when the user clicks the list's Refresh
  button, which sends ``?invalidate_cache=true``;
- **the generation of every list**, which changes when a user profile, an account or a resource's
  tags change, since those can alter what any list shows.

Invalidating a generation is a single cache delete, however many users and pages the list has,
and waits for the database transaction to commit, so that a request can't cache the old rows under
the new generation. A change made with ``QuerySet.update()`` sends no signal, so code that updates
a column that a list shows calls :func:`~smarter.lib.django.listview.invalidate_listview_cache`
afterwards, as the custom domain verification status and the MCPClient connection status do.
Pages expire after ``SMARTER_LISTVIEW_CACHE_EXPIRATION`` seconds, an hour by default, which bounds
how long any other such change can go unnoticed.

Adding a list
-------------

.. code-block:: python

    # apps/widget/views/listview/api.py
    class WidgetListApiView(SmarterListApiView):
        model = Widget
        serializer_class = WidgetSerializer
        listview_cache_kind = "Widget"
        sort_fields = SORT_FIELDS
        select_related = ("provider",)
        prefetch_related = ("widgetpart_set__part",)

    # apps/widget/receivers.py
    connect_listview_cache("Widget", "widget.Widget", "widget.WidgetPart", "provider.Provider")

A serializer method that reads a reverse relation uses
:func:`~smarter.lib.django.serializers.related_rows`, which reads the prefetched rows on a list
page, and queries them elsewhere.

.. automodule:: smarter.lib.django.listview
    :members:
    :undoc-members:
    :show-inheritance:
