"""
Pagination and search for the list apis of the React list views in the Smarter web console.

Every resource list, e.g. the Guardrail or Secret list, is a ``TabbedListView`` of
``@smarter/common``, which asks its Django list api for one page of the resources at a time,
optionally narrowed by a search and by one of the list's named filters, and sorted by one of its
columns. :func:`paginate_listview`
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

from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence

from django.core.exceptions import FieldDoesNotExist
from django.core.paginator import Page, Paginator
from django.db.models import F, Model, Q, QuerySet
from django.http import HttpRequest
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from smarter.lib.typing import SmarterDictType

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

DEFAULT_SORT_FIELDS: Mapping[str, str] = MappingProxyType(
    {
        "name": "name",
        "description": "description",
        "createdAt": "created_at",
        "updatedAt": "updated_at",
    }
)
"""The columns that a list may be sorted by, of the MetaDataModel that every Smarter resource inherits.

Each key is a column's name in the list api's response, in camelCase, as the ``ordering`` query
parameter names it. Each value is the field that sorts it, in the queryset's lookup syntax, such as
``"api_key__name"`` for a related resource's name.

It is read-only, since it is every list's default: a list adds its own columns to a copy, e.g.
``{**DEFAULT_SORT_FIELDS, "stage": "stage"}``.
"""


class ListViewPagination(BaseModel):
    """
    The description of one page of a list api's resources, as :func:`paginate_listview` returns it.

    Its JSON is camelCase, e.g. ``pageSize``.
    """

    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
    )

    page: int = Field(..., ge=1, description="The page's number, from 1.")
    page_size: int = Field(..., ge=1, le=MAX_PAGE_SIZE, description="The most resources that a page has.")
    num_pages: int = Field(..., ge=1, description="The number of pages.")
    count: int = Field(..., ge=0, description="The number of resources that match the search, on every page.")
    search: str = Field("", description="The search, or an empty string.")
    ordering: str = Field(
        "", description="The column that sorts the list, e.g. -createdAt, or an empty string for the default order."
    )
    sort_fields: list[str] = Field(default_factory=list, description="The columns that the list may be sorted by.")
    filter: str = Field(
        "", description="The named filter that narrows the list, e.g. pending, or an empty string for none."
    )
    filters: list[str] = Field(default_factory=list, description="The named filters that the list offers.")


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
    # pylint: disable=protected-access
    for field in search_fields:
        try:
            queryset.model._meta.get_field(field)
        except FieldDoesNotExist:
            continue
        condition |= Q(**{f"{field}__icontains": search})
    if not condition:
        return queryset
    return queryset.filter(condition)


def filter_queryset(queryset: QuerySet, name: str, filters: Mapping[str, Q]) -> tuple[QuerySet, str]:
    """
    The resources of ``queryset`` that match the named filter of ``filters``, e.g. ``"pending"``.

    A list offers its own named filters, so that a link can open it narrowed, e.g. the dashboard's
    pending deployments link opens the LLMClient list with ``?filter=pending``. An empty or
    unknown name leaves the queryset unchanged, as an unknown ordering does.

    :param queryset: The resources to filter.
    :param name: The filter's name, as the ``filter`` query parameter gives it.
    :param filters: The list's named filters, and the conditions that they apply.
    :returns: The matching resources, and the name of the filter that applied: ``name``, or an
        empty string if none did.
    """
    name = name.strip()
    condition = filters.get(name) if name else None
    if condition is None:
        return queryset, ""
    return queryset.filter(condition), name


def has_field(model: type[Model], lookup: str) -> bool:
    """
    Whether ``model`` has the field that ``lookup`` names, following relations, e.g. ``"api_key__name"``.

    :param model: The model whose field to look up.
    :param lookup: A field name, or a path of field names joined by ``__``.
    :returns: True if every field of the path exists.
    """
    # pylint: disable=protected-access
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


def paginate_queryset(
    queryset: QuerySet,
    page: Optional[str] = None,
    page_size: Optional[str] = None,
    search: str = "",
    ordering: str = "",
    list_filter: str = "",
    search_fields: Sequence[str] = DEFAULT_SEARCH_FIELDS,
    sort_fields: Mapping[str, str] = DEFAULT_SORT_FIELDS,
    filters: Optional[Mapping[str, Q]] = None,
) -> tuple[Page, SmarterDictType]:
    """
    One page of a list api's resources, which match its search, and a description of the page.

    The parameters are the list api's query parameters, as they arrived, so that a cached page can
    be built again from them without the request. See :func:`paginate_listview` for their meaning.

    :param queryset: The resources that the user may list, in their default order.
    :param page: The page's number, from 1. A page past the last is the last, and an invalid one is the first.
    :param page_size: The resources of a page, up to :data:`MAX_PAGE_SIZE`. :data:`DEFAULT_PAGE_SIZE` if invalid.
    :param search: Text that one of ``search_fields`` contains, ignoring case.
    :param ordering: The column of ``sort_fields`` to sort by, e.g. ``name``, or ``-name``. See :func:`sort_queryset`.
    :param list_filter: The name of one of ``filters``, e.g. ``pending``. See :func:`filter_queryset`.
    :param search_fields: The names of the fields that a search matches.
    :param sort_fields: The columns that the list may be sorted by, and the fields that sort them.
    :param filters: The list's named filters, and the conditions that they apply. None offers none.
    :returns: The page, and its description, a dumped :class:`ListViewPagination`.
    """
    search = (search or "").strip()[:MAX_SEARCH_LENGTH]
    size = positive_int(page_size, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE)
    filters = filters or {}
    queryset, applied_filter = filter_queryset(queryset, list_filter or "", filters)
    queryset, applied_ordering = sort_queryset(queryset, ordering or "", sort_fields)
    paginator = Paginator(search_queryset(queryset, search, search_fields), size)
    # get_page() returns the last page for a page past it, and the first for an invalid one.
    result = paginator.get_page(positive_int(page, 1))
    pagination = ListViewPagination(
        page=result.number,
        page_size=size,
        num_pages=paginator.num_pages,
        count=paginator.count,
        search=search,
        ordering=applied_ordering,
        sort_fields=sorted(sortable_fields(queryset, sort_fields)),
        filter=applied_filter,
        filters=sorted(filters),
    )
    return result, pagination.model_dump(mode="json")


def paginate_listview(
    request: HttpRequest,
    queryset: QuerySet,
    search_fields: Sequence[str] = DEFAULT_SEARCH_FIELDS,
    sort_fields: Mapping[str, str] = DEFAULT_SORT_FIELDS,
    filters: Optional[Mapping[str, Q]] = None,
) -> tuple[Page, SmarterDictType]:
    """
    One page of a list api's resources, which match its search, and a description of the page.

    The request's query parameters are all optional:

    - ``page``: from 1. A page past the last is the last, and an invalid one is the first.
    - ``page_size``: up to :data:`MAX_PAGE_SIZE`; :data:`DEFAULT_PAGE_SIZE` if invalid.
    - ``search``: text that one of ``search_fields`` contains, ignoring case.
    - ``ordering``: the column of ``sort_fields`` to sort by, e.g. ``name``, or ``-name`` to sort
      it in descending order. Without one, the resources keep the queryset's order. See
      :func:`sort_queryset`.
    - ``filter``: the name of one of ``filters``, e.g. ``pending``. See :func:`filter_queryset`.

    :param request: The list api's request.
    :param queryset: The resources that the user may list, in their default order.
    :param search_fields: The names of the fields that a search matches.
    :param sort_fields: The columns that the list may be sorted by, and the fields that sort them.
        See :data:`DEFAULT_SORT_FIELDS`.
    :param filters: The list's named filters, and the conditions that they apply, e.g.
        ``{"pending": Q(deployed=False)}``. None offers none.
    :returns: The page, and its description for the list api's response, a dumped :class:`ListViewPagination`:
        ``{"page": 1, "pageSize": 25, "numPages": 3, "count": 61, "search": "", "ordering": "-name",
        "sortFields": ["createdAt", "description", "name", "updatedAt"], "filter": "", "filters": []}``. ``ordering`` is empty
        when the default order applies, and ``sortFields`` are the columns that the list may be
        sorted by, so that the list shows only those columns as sortable.
    """
    return paginate_queryset(
        queryset,
        page=request.GET.get("page"),
        page_size=request.GET.get("page_size"),
        search=request.GET.get("search", ""),
        ordering=request.GET.get("ordering", ""),
        list_filter=request.GET.get("filter", ""),
        search_fields=search_fields,
        sort_fields=sort_fields,
        filters=filters,
    )


__all__ = [
    "DEFAULT_PAGE_SIZE",
    "DEFAULT_SEARCH_FIELDS",
    "DEFAULT_SORT_FIELDS",
    "ListViewPagination",
    "MAX_PAGE_SIZE",
    "MAX_SEARCH_LENGTH",
    "filter_queryset",
    "has_field",
    "paginate_listview",
    "paginate_queryset",
    "positive_int",
    "search_queryset",
    "sort_queryset",
    "sortable_fields",
]
