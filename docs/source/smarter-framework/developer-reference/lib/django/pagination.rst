List Pagination, Search and Sorting
===================================

Every resource list in the web console, e.g. the Guardrail, Secret or Prompt list, shows one
page of resources at a time, with previous and next page buttons, a page number box, and a
search, and its column headers sort it. Its Django list api, at
``react-integration/api/listview/<owned|shared|all>/``, does the paging, the searching and the
sorting, so a search covers all of the resources that the user may list, and a sort orders all
of them, not only those of the page shown.

The api's optional query parameters are ``page``, from 1; ``page_size``, up to 100, and 25 by
default; ``search``, the text that a resource's name or description contains, ignoring case; and
``ordering``, the column to sort by, such as ``name``, or ``-name`` to sort it in descending
order. Without an ordering, the most recently updated resources come first. Its response
describes the page that it returns, alongside its ``objects``:

.. code-block:: json

    {
        "objects": [{"name": "my_guardrail", "...": "..."}],
        "pagination": {
            "page": 2,
            "pageSize": 25,
            "numPages": 3,
            "count": 61,
            "search": "guard",
            "ordering": "-name",
            "sortFields": ["category", "createdAt", "description", "name", "stage", "updatedAt"]
        }
    }

A page past the last is the last, and an invalid page or page size is the default. Every list
api implements this with :func:`~smarter.lib.django.pagination.paginate_listview`.

Each list api names the columns that it can sort by, in camelCase as its ``objects`` name them,
and the model field that sorts each one, e.g. ``"apiKey": "api_key__name"`` for a Provider's API
key. Every list can sort by ``name``, ``description``, ``createdAt`` and ``updatedAt``
(:data:`~smarter.lib.django.pagination.DEFAULT_SORT_FIELDS`), and most add the columns of their
own resource, such as a Guardrail's ``stage`` and ``category``. An unknown ordering is ignored,
and ``sortFields`` lists the columns that the api can sort by, so that the React list makes only
those column headers clickable. Each click on a header cycles its column through ascending,
descending and the default order, and returns the list to its first page. Resources whose column
has the same value are ordered by their primary key, so that each appears on exactly one page.

.. automodule:: smarter.lib.django.pagination
    :members:
    :undoc-members:
    :show-inheritance:
