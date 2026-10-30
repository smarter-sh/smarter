"""
The dashboard's global search: find the Smarter resources of every kind that a user may read.

The search box on the dashboard sends one query, which is one of:

- **text**, e.g. ``support``: resources whose name or description contains it, ignoring case, or
  that have the tag ``support``;
- **a tag**, ``tag:production``: resources that have the tag ``production``;
- **an annotation selector requirement**, e.g. ``acme.com/crm-account-id=A-10042`` or
  ``!acme.com/archived``: see :mod:`smarter.lib.annotation.selectors`. Text that contains ``=``, or
  begins with ``!``, is a requirement. Text with a ``/`` and no spaces is a requirement when it is a
  valid annotation key, e.g. ``acme.com/crm-account-id``, and text otherwise.

Every list of the web console (:func:`smarter.lib.django.listview.listview_registry`) is searched
with its list api's own queryset, so a user finds only what their lists show them, and with its own
serializer, so each result links to the same page as the list does. The results are grouped by
list, a few per list, each group with a link to its list, narrowed by the same query.
"""

from typing import Literal, Optional
from urllib.parse import urlencode

from django.db.models import Q, QuerySet
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from smarter.lib import logging
from smarter.lib.annotation.selectors import (
    filter_by_annotations,
    parse_annotation_requirement,
)
from smarter.lib.annotation.validation import SmarterAnnotationError
from smarter.lib.django.listview import (
    ListviewEntry,
    ListviewPageRequest,
    listview_registry,
)
from smarter.lib.django.pagination import MAX_SEARCH_LENGTH, has_field, tag_condition

logger = logging.getLogger(__name__)
logger_prefix = logging.SmarterFormattedText.text(__name__)

TAG_PREFIX = "tag:"
"""The prefix of a query that finds the resources with a tag, e.g. ``tag:production``."""

MAX_RESULTS_PER_LIST = 5
"""The most results that a list's group shows.

Its link shows the rest.
"""

SearchMode = Literal["text", "tag", "annotation"]
"""How a query was understood."""


class GlobalSearchModel(BaseModel):
    """Base class of the global search's models, whose JSON is camelCase."""

    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
    )


class GlobalSearchResult(GlobalSearchModel):
    """One resource that matches the query."""

    name: str = Field(..., description="The resource's name.")
    description: str = Field(default="", description="The resource's description.")
    url: str = Field(..., description="The resource's page in the web console.")


class GlobalSearchGroup(GlobalSearchModel):
    """The resources of one list that match the query."""

    label: str = Field(..., description="The list's name, e.g. Guardrails.")
    count: int = Field(..., ge=1, description="How many of the list's resources match.")
    url: str = Field(..., description="The list's page, narrowed by the query.")
    results: list[GlobalSearchResult] = Field(
        default_factory=list, description=f"The first {MAX_RESULTS_PER_LIST} matches, the most recently updated first."
    )


class GlobalSearchResponse(GlobalSearchModel):
    """The response of the global search."""

    query: str = Field(default="", description="The query, as it was searched.")
    mode: SearchMode = Field(default="text", description="How the query was understood.")
    error: str = Field(default="", description="Why the query is invalid, or an empty string.")
    count: int = Field(default=0, ge=0, description="How many resources match, in every list.")
    groups: list[GlobalSearchGroup] = Field(default_factory=list, description="The lists that have matches.")


def parse_query(query: str) -> tuple[SearchMode, str, str]:
    """
    Return how a query is understood: its mode, the value to search for, and an error, if any.

    **Example:**

    .. code-block:: python

        parse_query("support")              # ("text", "support", "")
        parse_query("tag:production")       # ("tag", "production", "")
        parse_query("acme.com/crm-id=A-1")  # ("annotation", "acme.com/crm-id=A-1", "")
        parse_query("https://example.com")  # ("text", "https://example.com", "")

    :param query: The query, as typed.
    :returns: The mode, the value, and why the query is invalid, or an empty string.
    """
    query = query.strip()[:MAX_SEARCH_LENGTH]
    if query.lower().startswith(TAG_PREFIX):
        return "tag", query[len(TAG_PREFIX) :].strip(), ""
    explicit = "=" in query or query.startswith("!")
    possible = "/" in query and " " not in query
    if explicit or possible:
        try:
            return "annotation", str(parse_annotation_requirement(query)), ""
        except SmarterAnnotationError as e:
            if explicit:
                return "annotation", query, e.message
    return "text", query, ""


def match(entry: ListviewEntry, queryset: QuerySet, mode: SearchMode, value: str) -> QuerySet:
    """
    Return the resources of a list's queryset that match the query.

    :param entry: The list.
    :param queryset: The resources that the user may read, from the list api.
    :param mode: How the query was understood.
    :param value: The value to search for.
    :returns: The matching resources.
    """
    model = queryset.model
    if mode == "tag":
        tagged = tag_condition(model, value)
        return queryset.filter(tagged) if tagged is not None else queryset.none()
    if mode == "annotation":
        return filter_by_annotations(queryset, [value])
    condition = Q()
    for field in entry.view_class.search_fields:
        if has_field(model, field):
            condition |= Q(**{f"{field}__icontains": value})
    tagged = tag_condition(model, value)
    if tagged is not None:
        condition |= tagged
    if not condition:
        return queryset.none()
    # pk__in, rather than filter(condition).distinct(), so that the tag join doesn't repeat a resource.
    return queryset.filter(pk__in=queryset.filter(condition).values("pk"))


def list_url(entry: ListviewEntry, mode: SearchMode, value: str) -> str:
    """
    Return the url of a list's page, narrowed by the query, as its TabbedListView reads it.

    :param entry: The list.
    :param mode: How the query was understood.
    :param value: The value to search for.
    :returns: The url, e.g. ``/guardrail/?tag=production``.
    """
    parameter = {"text": "search", "tag": "tag", "annotation": "annotation"}[mode]
    return f"{entry.page_url}?{urlencode({parameter: value})}"


def detail_page_url(entry: ListviewEntry, row: dict) -> Optional[str]:
    """
    Return the url of a resource's list, narrowed by its name, with the resource's detail open.

    The list's TabbedListView opens the detail of ``?detail=<record locator>``: the resource's manifest, what it
    uses and what uses it, beside its own fields. The record locator is the last part of the row's
    ``detailUrl``, which :class:`smarter.apps.account.serializers.MetaDataWithOwnershipModelSerializer` adds.

    :param entry: The resource's list.
    :param row: The serialized resource.
    :returns: The url, e.g. ``/secret/?search=openai_api_key&detail=secret-rMTAwx``, or None if the row has no
        detail.
    """
    detail_url = row.get("detail_url") or row.get("detailUrl")
    record_locator = str(detail_url or "").rstrip("/").rsplit("/", 1)[-1]
    if not record_locator:
        return None
    return f"{entry.page_url}?{urlencode({'search': str(row.get('name') or ''), 'detail': record_locator})}"


def result_of(row: dict, fallback_url: str, detail_url: Optional[str] = None) -> GlobalSearchResult:
    """
    Return a search result from a resource as its list api's serializer dumps it.

    A result opens the resource's detail in its list (see :func:`detail_page_url`). A resource that has no
    detail opens its page, which serializers name ``manifest_url``, or ``manifestUrl`` when they camel-case.

    :param row: The serialized resource.
    :param fallback_url: The url to link to when the serializer gives neither: its list, narrowed by its name.
    :param detail_url: Its list, with its detail open.
    :returns: The result.
    """
    url = detail_url or row.get("manifest_url") or row.get("manifestUrl") or fallback_url
    return GlobalSearchResult(
        name=str(row.get("name") or ""),
        description=str(row.get("description") or ""),
        url=str(url),
    )


def global_search(user, query: str, entries: Optional[tuple[ListviewEntry, ...]] = None) -> GlobalSearchResponse:
    """
    Search every list of the web console for the resources that match a query and that the user may read.

    :param user: The authenticated user.
    :param query: The query, as typed. See :func:`parse_query`.
    :param entries: The lists to search. Every list, by default.
    :returns: The results, grouped by list, the lists with the most matches first.
    """
    mode, value, error = parse_query(query)
    response = GlobalSearchResponse(query=value, mode=mode, error=error)
    if error or not value:
        return response
    request = ListviewPageRequest(user)
    for entry in listview_registry() if entries is None else entries:
        view_class = entry.view_class
        try:
            matches = match(entry, view_class.get_queryset(user, "all"), mode, value)
            count = matches.count()
            if not count:
                continue
            rows = view_class.serializer_class(
                matches[:MAX_RESULTS_PER_LIST], many=True, context={"request": request}
            ).data
        # one list's failure must not hide the others' results.
        # pylint: disable=broad-exception-caught
        except Exception as e:
            logger.error("%s.global_search() searching %s failed: %s", logger_prefix, entry.label, e)
            continue
        url = list_url(entry, mode, value)
        response.groups.append(
            GlobalSearchGroup(
                label=entry.label,
                count=count,
                url=url,
                results=[
                    result_of(
                        dict(row),
                        list_url(entry, "text", str(row.get("name") or "")),
                        detail_page_url(entry, dict(row)),
                    )
                    for row in rows
                ],
            )
        )
        response.count += count
    response.groups.sort(key=lambda group: (-group.count, group.label))
    return response


__all__ = [
    "detail_page_url",
    "GlobalSearchGroup",
    "GlobalSearchResponse",
    "GlobalSearchResult",
    "global_search",
    "list_url",
    "parse_query",
]
