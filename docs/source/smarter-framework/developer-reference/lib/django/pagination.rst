List Pagination and Search
==========================

Every resource list in the web console, e.g. the Guardrail, Secret or Prompt list, shows one
page of resources at a time, with previous and next page buttons, a page number box, and a
search. Its Django list api, at ``react-integration/api/listview/<owned|shared|all>/``, does the
paging and the searching, so a search covers all of the resources that the user may list, not
only those of the page shown.

The api's optional query parameters are ``page``, from 1; ``page_size``, up to 100, and 25 by
default; and ``search``, the text that a resource's name or description contains, ignoring case.
Its response describes the page that it returns, alongside its ``objects``:

.. code-block:: json

    {
        "objects": [{"name": "my_guardrail", "...": "..."}],
        "pagination": {"page": 2, "pageSize": 25, "numPages": 3, "count": 61, "search": "guard"}
    }

A page past the last is the last, and an invalid page or page size is the default. Every list
api implements this with :func:`~smarter.lib.django.pagination.paginate_listview`.

.. automodule:: smarter.lib.django.pagination
    :members:
    :undoc-members:
    :show-inheritance:
