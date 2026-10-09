"""
Pagination and search for the list apis of the React list views in the Smarter web console.

Every resource list, e.g. the Guardrail or Secret list, is a ``TabbedListView`` of
``@smarter/common``, which asks its Django list api for one page of the resources at a time,
optionally narrowed by a search, and sorted by one of its columns. :func:`paginate_listview`
reads those query parameters, filters, sorts and paginates the queryset, and describes the page,
so that every list api behaves alike.

The list is sorted by the database, not in the browser, because a page holds only some of the
resources: sorting the rows of the page shown would leave the rest of the resources in their
default order, on the other pages.

.. code-block:: python

    SORT_FIELDS = {**DEFAULT_SORT_FIELDS, "stage": "stage"}

    page, pagination = paginate_listview(request, qs.order_by("-updated_at"), sort_fields=SORT_FIELDS)
    return JsonResponse(
        {
            "objects": GuardrailSerializer(page, many=True, context={"request": request}).data,
            "pagination": pagination,
        }
    )
"""

from typing import Any, Mapping, Optional, Sequence

from django.core.exceptions import FieldDoesNotExist
from django.core.paginator import Page, Paginator
from django.db.models import F, Model, Q, QuerySet
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

DEFAULT_SORT_FIELDS: Mapping[str, str] = {
    "name": "name",
    "description": "description",
    "createdAt": "created_at",
    "updatedAt": "updated_at",
}
"""The columns that a list may be sorted by, of the MetaDataModel that every Smarter resource inherits.

Each key is a column's name in the list api's response, in camelCase, as the ``ordering`` query
parameter names it. Each value is the field that sorts it, in the queryset's lookup syntax, such as
``"api_key__name"`` for a related resource's name.
"""


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


def has_field(model: type[Model], lookup: str) -> bool:
    """
    Whether ``model`` has the field that ``lookup`` names, following relations, e.g. ``"api_key__name"``.

    :param model: The model whose field to look up.
    :param lookup: A field name, or a path of field names joined by ``__``.
    :returns: True if every field of the path exists.
    """
    for name in lookup.split("__"):
        if model is None:
            return False
        try:
            field = model._meta.get_field(name)
        except FieldDoesNotExist:
            return False
        model = field.related_model  # type: ignore[assignment]
    return True


def sortable_fields(queryset: QuerySet, sort_fields: Mapping[str, str] = DEFAULT_SORT_FIELDS) -> dict[str, str]:
    """
    The columns of ``sort_fields`` that the queryset's model can be sorted by.

    :param queryset: The resources to sort.
    :param sort_fields: The columns that the list may be sorted by, and the fields that sort them.
    :returns: Those of ``sort_fields`` whose field the model has.
    """
    return {column: lookup for column, lookup in sort_fields.items() if has_field(queryset.model, lookup)}


def sort_queryset(
    queryset: QuerySet, ordering: str, sort_fields: Mapping[str, str] = DEFAULT_SORT_FIELDS
) -> tuple[QuerySet, str]:
    """
    The resources of ``queryset``, sorted by the column that ``ordering`` names.

    ``ordering`` is a column of ``sort_fields``, such as ``"name"``, or, to sort it in descending
    order, the column after a minus sign, such as ``"-name"``. Empty values sort after the others,
    in either direction. An empty or unknown ordering leaves the queryset's own order.

    The resources' primary key breaks ties, in the same direction, so that resources whose column
    has the same value, e.g. the same stage, are in the same order on every request. Otherwise the
    database could return them in a different order for each page, and a resource could appear on
    two pages, or on none.

    :param queryset: The resources to sort, in their default order.
    :param ordering: The column to sort by, optionally after a minus sign.
    :param sort_fields: The columns that the list may be sorted by, and the fields that sort them.
    :returns: The sorted resources, and the ordering that sorted them: ``ordering``, or an empty
        string if the queryset kept its own order.
    """
    ordering = ordering.strip()
    descending = ordering.startswith("-")
    column = ordering[1:] if descending else ordering
    lookup = sortable_fields(queryset, sort_fields).get(column)
    if not lookup:
        if queryset.query.order_by:
            queryset = queryset.order_by(*queryset.query.order_by, "-pk")
        return queryset, ""
    if descending:
        return queryset.order_by(F(lookup).desc(nulls_last=True), "-pk"), ordering
    return queryset.order_by(F(lookup).asc(nulls_last=True), "pk"), ordering


def paginate_listview(
    request: HttpRequest,
    queryset: QuerySet,
    search_fields: Sequence[str] = DEFAULT_SEARCH_FIELDS,
    sort_fields: Mapping[str, str] = DEFAULT_SORT_FIELDS,
) -> tuple[Page, dict[str, Any]]:
    """
    One page of a list api's resources, which match its search, and a description of the page.

    The request's query parameters are all optional:

    - ``page``: from 1. A page past the last is the last, and an invalid one is the first.
    - ``page_size``: up to :data:`MAX_PAGE_SIZE`; :data:`DEFAULT_PAGE_SIZE` if invalid.
    - ``search``: text that one of ``search_fields`` contains, ignoring case.
    - ``ordering``: the column of ``sort_fields`` to sort by, e.g. ``name``, or ``-name`` to sort
      it in descending order. Without one, the resources keep the queryset's order. See
      :func:`sort_queryset`.

    :param request: The list api's request.
    :param queryset: The resources that the user may list, in their default order.
    :param search_fields: The names of the fields that a search matches.
    :param sort_fields: The columns that the list may be sorted by, and the fields that sort them.
        See :data:`DEFAULT_SORT_FIELDS`.
    :returns: The page, and its description for the list api's response:
        ``{"page": 1, "pageSize": 25, "numPages": 3, "count": 61, "search": "", "ordering": "-name",
        "sortFields": ["createdAt", "description", "name", "updatedAt"]}``. ``ordering`` is empty
        when the default order applies, and ``sortFields`` are the columns that the list may be
        sorted by, so that the list shows only those columns as sortable.
    """
    search = request.GET.get("search", "").strip()[:MAX_SEARCH_LENGTH]
    page_size = positive_int(request.GET.get("page_size"), DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE)
    queryset, ordering = sort_queryset(queryset, request.GET.get("ordering", ""), sort_fields)
    paginator = Paginator(search_queryset(queryset, search, search_fields), page_size)
    # get_page() returns the last page for a page past it, and the first for an invalid one.
    page = paginator.get_page(positive_int(request.GET.get("page"), 1))
    pagination = {
        "page": page.number,
        "pageSize": page_size,
        "numPages": paginator.num_pages,
        "count": paginator.count,
        "search": search,
        "ordering": ordering,
        "sortFields": sorted(sortable_fields(queryset, sort_fields)),
    }
    return page, pagination


__all__ = [
    "DEFAULT_PAGE_SIZE",
    "DEFAULT_SEARCH_FIELDS",
    "DEFAULT_SORT_FIELDS",
    "MAX_PAGE_SIZE",
    "MAX_SEARCH_LENGTH",
    "has_field",
    "paginate_listview",
    "positive_int",
    "search_queryset",
    "sort_queryset",
    "sortable_fields",
]
