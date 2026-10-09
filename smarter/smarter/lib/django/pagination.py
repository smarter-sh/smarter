"""
Pagination and search for the list apis of the React list views in the Smarter web console.

Every resource list, e.g. the Guardrail or Secret list, is a ``TabbedListView`` of
``@smarter/common``, which asks its Django list api for one page of the resources at a time,
optionally narrowed by a search. :func:`paginate_listview` reads those query parameters, filters
and paginates the queryset, and describes the page, so that every list api behaves alike.

.. code-block:: python

    page, pagination = paginate_listview(request, qs.order_by("-updated_at"))
    return JsonResponse(
        {
            "objects": GuardrailSerializer(page, many=True, context={"request": request}).data,
            "pagination": pagination,
        }
    )
"""

from typing import Any, Optional, Sequence

from django.core.exceptions import FieldDoesNotExist
from django.core.paginator import Page, Paginator
from django.db.models import Q, QuerySet
from django.http import HttpRequest

DEFAULT_PAGE_SIZE = 25
"""The resources of a page, unless the list asks for another number."""

MAX_PAGE_SIZE = 100
"""The most resources that a page may have."""

MAX_SEARCH_LENGTH = 255
"""The longest search, in characters.

A longer one is truncated.
"""

DEFAULT_SEARCH_FIELDS = ("name", "description")
"""The fields that a search matches, of the MetaDataModel that every Smarter resource inherits."""


def positive_int(value: Any, default: int, maximum: Optional[int] = None) -> int:
    """
    An integer query parameter, from 1 up to ``maximum``, if any, or else ``default``.

    :param value: The query parameter, a string such as ``"2"``, or ``None`` when it is missing.
    :param default: The value for a missing, invalid, or out of range parameter.
    :param maximum: The largest value allowed, if any.
    :returns: The parameter as an integer, or ``default``.
    """
    try:
        retval = int(value)
    except (TypeError, ValueError):
        return default
    if retval < 1 or (maximum is not None and retval > maximum):
        return default
    return retval


def search_queryset(queryset: QuerySet, search: str, search_fields: Sequence[str] = DEFAULT_SEARCH_FIELDS) -> QuerySet:
    """
    The resources of ``queryset`` that one of ``search_fields`` contains ``search`` in, ignoring case.

    Fields that the queryset's model does not have are ignored. An empty search, or one with no
    field to match, returns the queryset unchanged.

    :param queryset: The resources to search.
    :param search: The text to search for.
    :param search_fields: The names of the fields to search.
    :returns: The matching resources.
    """
    search = search.strip()[:MAX_SEARCH_LENGTH]
    if not search:
        return queryset
    condition = Q()
    for field in search_fields:
        try:
            queryset.model._meta.get_field(field)
        except FieldDoesNotExist:
            continue
        condition |= Q(**{f"{field}__icontains": search})
    if not condition:
        return queryset
    return queryset.filter(condition)


def paginate_listview(
    request: HttpRequest,
    queryset: QuerySet,
    search_fields: Sequence[str] = DEFAULT_SEARCH_FIELDS,
) -> tuple[Page, dict[str, Any]]:
    """
    One page of a list api's resources, which match its search, and a description of the page.

    The request's query parameters are all optional:

    - ``page``: from 1. A page past the last is the last, and an invalid one is the first.
    - ``page_size``: up to :data:`MAX_PAGE_SIZE`; :data:`DEFAULT_PAGE_SIZE` if invalid.
    - ``search``: text that one of ``search_fields`` contains, ignoring case.

    :param request: The list api's request.
    :param queryset: The resources that the user may list, ordered.
    :param search_fields: The names of the fields that a search matches.
    :returns: The page, and its description for the list api's response:
        ``{"page": 1, "pageSize": 25, "numPages": 3, "count": 61, "search": ""}``.
    """
    search = request.GET.get("search", "").strip()[:MAX_SEARCH_LENGTH]
    page_size = positive_int(request.GET.get("page_size"), DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE)
    paginator = Paginator(search_queryset(queryset, search, search_fields), page_size)
    # get_page() returns the last page for a page past it, and the first for an invalid one.
    page = paginator.get_page(positive_int(request.GET.get("page"), 1))
    pagination = {
        "page": page.number,
        "pageSize": page_size,
        "numPages": paginator.num_pages,
        "count": paginator.count,
        "search": search,
    }
    return page, pagination


__all__ = [
    "DEFAULT_PAGE_SIZE",
    "DEFAULT_SEARCH_FIELDS",
    "MAX_PAGE_SIZE",
    "MAX_SEARCH_LENGTH",
    "paginate_listview",
    "positive_int",
    "search_queryset",
]
