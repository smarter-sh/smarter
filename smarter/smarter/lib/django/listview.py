"""
Cached pages for the list apis of the React list views in the Smarter web console.

Every resource list, e.g. the LLMClient or Secret list, asks its Django list api for one page of
its resources at a time (see :mod:`smarter.lib.django.pagination`). :class:`SmarterListApiView` is
the base class of those apis. It builds the page's whole response once, and caches it in Redis
with :func:`~cache_results.decorators.cache_results`, per user and per page, so that the next request for
the same page costs a few cache reads instead of a query and a serializer per resource.

The cached pages stay correct because their cache key includes three *generations*, each a value
from :func:`listview_cache_generation` that changes when it is invalidated:

- the list's generation, e.g. ``LLMClient``'s, which changes whenever a resource that the list
  shows is saved or deleted (see :func:`connect_listview_cache`);
- the user's generation of the list, which changes when the user asks for a fresh list, with the
  list api's ``invalidate_cache=true``;
- the generation of every list, :data:`LISTVIEW_CACHE_ALL`, which changes whenever a change can
  alter what any list shows, such as a user's profile, an account, or a resource's tags or annotations.

A new generation leaves the previous pages unread, until they expire after
``smarter_settings.listview_cache_expiration`` seconds. So invalidating a list is a single cache
delete, however many users and pages it has.

.. code-block:: python

    # an app's receivers.py, which its AppConfig.ready() imports, so that the Celery workers
    # invalidate the list too
    connect_listview_cache("Guardrail", "guardrail.Guardrail", "llmclient.LLMClientGuardrails")

    # the app's views/listview/api.py
    class GuardrailListApiView(SmarterListApiView):
        model = Guardrail
        serializer_class = GuardrailSerializer
        listview_cache_kind = "Guardrail"
"""

import functools
import json
import time
from http import HTTPStatus
from typing import (
    Callable,
    ClassVar,
    Mapping,
    NamedTuple,
    Optional,
    Protocol,
    Sequence,
    Union,
)
from urllib.parse import urlparse

from cache_results import cache_results
from django.apps import apps
from django.contrib.auth.models import User
from django.core.exceptions import FieldDoesNotExist
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models, transaction
from django.db.models import Prefetch, Q
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.http import HttpRequest, JsonResponse
from django.urls import NoReverseMatch, URLPattern, URLResolver, get_resolver
from django.urls import reverse as django_reverse
from django.utils.module_loading import import_string
from rest_framework import serializers

from smarter.common.conf import smarter_settings
from smarter.common.enum import SmarterResourceOwnershipFilterEnum
from smarter.lib import logging
from smarter.lib.django.pagination import (
    DEFAULT_SEARCH_FIELDS,
    DEFAULT_SORT_FIELDS,
    MAX_LIST_ANNOTATIONS,
    MAX_LIST_TAGS,
    clean_query_values,
    has_field,
    paginate_queryset,
)
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.typing import SmarterDictType

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.CACHE_LOGGING])
logger_prefix = logging.SmarterFormattedText.text(__name__)

LISTVIEW_CACHE_ALL = "*"
"""The generation of every list: invalidating it makes the cached pages of every list stale."""

OWNERSHIP_FILTERS = (
    SmarterResourceOwnershipFilterEnum.OWNED,
    SmarterResourceOwnershipFilterEnum.SHARED,
    SmarterResourceOwnershipFilterEnum.ALL,
)
"""The ownership filters that a list api accepts, as the last segment of its url."""

LISTVIEW_OWNER_RELATIONS = ("user_profile__user", "user_profile__account")
"""The relations of every owned resource that its serializer reads, joined into the list's query."""


# pylint: disable=W2301
class OwnershipManager(Protocol):
    """
    The manager of a resource that a list api lists: it filters the resources by who may see them.

    E.g. the manager of every MetaDataWithOwnershipModel, and SmarterAuthToken's.
    """

    def owned_by(self, user: User) -> models.QuerySet:
        """The resources that the user owns."""
        ...

    def shared_with(self, user: User) -> models.QuerySet:
        """The resources that the user may read, but doesn't own."""
        ...

    def with_read_permission_for(self, user: User) -> models.QuerySet:
        """The resources that the user may read."""
        ...


@cache_results(timeout=smarter_settings.listview_cache_expiration)
def listview_cache_generation(kind: str, user_profile_id: Optional[int] = None) -> int:  # pylint: disable=W0613
    """
    Return the current generation of a list's cached pages.

    The generation is any value that changes when it is invalidated: the time of the first call
    after the last invalidation, in nanoseconds. It is part of the cache key of every cached page,
    so invalidating it makes all of them stale at once.

    :param kind: The list, e.g. ``LLMClient``, or :data:`LISTVIEW_CACHE_ALL` for every list.
    :param user_profile_id: The user profile whose pages of the list it is, or None for every user's.
    :returns: The generation.
    """
    return time.time_ns()


def invalidate_listview_cache(kind: str, user_profile_id: Optional[int] = None) -> None:
    """
    Make the cached pages of a list stale, once the current transaction commits.

    Waiting for the commit keeps a request that reads the database before the change commits
    from caching the old rows under the new generation. Outside a transaction, it happens at once.

    :param kind: The list, e.g. ``LLMClient``, or :data:`LISTVIEW_CACHE_ALL` for every list.
    :param user_profile_id: The user profile whose pages to make stale, or None for every user's.
    """
    logger.debug("%s.invalidate_listview_cache() kind=%s user_profile_id=%s", logger_prefix, kind, user_profile_id)
    transaction.on_commit(lambda: listview_cache_generation.invalidate(kind, user_profile_id))


def _listview_cache_receiver(kind: str) -> Callable[..., None]:
    """Return a signal receiver that invalidates a list's cached pages."""

    def receiver(sender, **kwargs) -> None:  # pylint: disable=W0613
        # m2m_changed sends pre_ and post_ actions; a change is complete only after the post_ ones.
        action = kwargs.get("action")
        if action is not None and not str(action).startswith("post_"):
            return
        invalidate_listview_cache(kind)

    return receiver


def connect_listview_cache(kind: str, *model_labels: str) -> None:
    """
    Invalidate a list's cached pages whenever one of these models is saved or deleted.

    Call it from an app's ``receivers.py``, which its ``AppConfig.ready()`` imports, so that every
    process connects it, including the Celery workers, which save resources too. List every
    model whose rows the list's serializer shows: the resource, and the related models that it
    nests, e.g. an LLMClient's plugins. A many-to-many model is invalidated by ``m2m_changed``
    too, since ``add()`` and ``remove()`` save no row through ``save()``.

    Each model's proxy models and multi-table children are connected too, since they send their
    signals as themselves. A change made with ``QuerySet.update()`` sends no signal. Call :func:`invalidate_listview_cache`
    after it, if the list shows what it changes.

    :param kind: The list, e.g. ``LLMClient``, or :data:`LISTVIEW_CACHE_ALL` for every list.
    :param model_labels: The models, as ``app_label.ModelName``, e.g. ``llmclient.LLMClientPlugin``.
    """
    receiver = _listview_cache_receiver(kind)
    for label in model_labels:
        model = apps.get_model(label)
        # a proxy model, e.g. PluginMetaStatic, or a multi-table child, e.g. ApiConnection, sends its
        # signals as itself, not as the model that it extends.
        senders = [candidate for candidate in apps.get_models() if issubclass(candidate, model)]
        for sender in senders:
            dispatch_uid = f"{__name__}.{kind}.{sender._meta.label}"  # pylint: disable=W0212
            post_save.connect(receiver, sender=sender, weak=False, dispatch_uid=f"{dispatch_uid}.post_save")
            post_delete.connect(receiver, sender=sender, weak=False, dispatch_uid=f"{dispatch_uid}.post_delete")
            m2m_changed.connect(receiver, sender=sender, weak=False, dispatch_uid=f"{dispatch_uid}.m2m_changed")


def _is_relation(model: type[models.Model], name: str) -> bool:
    """Whether ``model`` has a field named ``name`` that is a relation, e.g. a taggit ``tags`` manager, not a JSON list."""
    # pylint: disable=protected-access
    try:
        return bool(model._meta.get_field(name).is_relation)
    except FieldDoesNotExist:
        return False


class ListviewPageRequest(HttpRequest):
    """
    The request that a cached list page is serialized with, which no http request is.

    A cached page is shared by every request of the user, so it is built without one. Its
    serializer still needs a user, since ``can_delete`` depends on it, and a host and scheme,
    since a file field, e.g. a Provider's ``logo``, is made an absolute url with
    ``request.build_absolute_uri()``. Both are the platform's, :attr:`smarter_settings.environment_url`.

    :param user: The user whose page it is.
    """

    def __init__(self, user: User):
        super().__init__()
        url = urlparse(smarter_settings.environment_url)
        self.user = user
        self.META["HTTP_HOST"] = url.netloc
        self._listview_scheme = url.scheme or "https"

    def _get_scheme(self) -> str:
        """Return the platform's scheme, instead of HttpRequest's ``http``."""
        return self._listview_scheme


@cache_results(timeout=smarter_settings.listview_cache_expiration)
def cached_listview_page(  # pylint: disable=W0613,R0913,R0917
    view: str,
    kind_generation: int,
    user_generation: int,
    all_generation: int,
    user_profile_id: int,
    ownership_filter: str,
    page: Optional[str],
    page_size: Optional[str],
    search: str,
    ordering: str,
    list_filter: str,
    tags: tuple[str, ...] = (),
    annotations: tuple[str, ...] = (),
) -> SmarterDictType:
    """
    Return one page of a list api's response, from the cache when it holds it.

    Its parameters are the cache key: everything that can change the page. The generations are
    not read, but they make the page stale when the list changes (see :func:`listview_cache_generation`).

    :param view: The list api's class, as a dotted path, whose :meth:`SmarterListApiView.build_page` builds the page.
    :param kind_generation: The list's generation.
    :param user_generation: The user's generation of the list.
    :param all_generation: The generation of every list.
    :param user_profile_id: The user profile whose page it is.
    :param ownership_filter: ``owned``, ``shared`` or ``all``.
    :param page: The ``page`` query parameter, as it arrived.
    :param page_size: The ``page_size`` query parameter, as it arrived.
    :param search: The ``search`` query parameter.
    :param ordering: The ``ordering`` query parameter.
    :param list_filter: The ``filter`` query parameter.
    :param tags: The ``tag`` query parameters, cleaned with :func:`~smarter.lib.django.pagination.clean_query_values`.
    :param annotations: The ``annotation`` query parameters, cleaned the same way.
    :returns: The list api's response, as JSON-compatible values.
    """
    # pylint: disable=C0415
    from smarter.apps.account.models import UserProfile

    view_class: type[SmarterListApiView] = import_string(view)
    user_profile = UserProfile.objects.select_related("user", "account").get(id=user_profile_id)
    logger.debug(
        "%s.cached_listview_page() building %s page=%s for user_profile %s", logger_prefix, view, page, user_profile_id
    )
    return view_class.build_page(
        user_profile,
        ownership_filter,
        page=page,
        page_size=page_size,
        search=search,
        ordering=ordering,
        list_filter=list_filter,
        tags=tags,
        annotations=annotations,
    )


class SmarterListApiView(SmarterAuthenticatedNeverCachedWebView):
    """
    The base class of the list apis of the web console's React list views.

    A list api returns one page of the resources that the authenticated user owns, that are
    shared with them, or both, as ``{"user": ..., "admin": ..., "objects": [...], "pagination": {...}}``.
    The page is cached per user (see :func:`cached_listview_page`), and ``?invalidate_cache=true``
    makes the user's cached pages of the list stale first, for the list's Refresh button.

    A subclass sets :attr:`model`, :attr:`serializer_class` and :attr:`listview_cache_kind`, and
    names the relations that its serializer reads in :attr:`select_related` and
    :attr:`prefetch_related`, so that a page costs a few queries, however many resources it has.
    The resource's owner and tags, when it has them, are always fetched with it, and the
    annotations of the page's resources are read in one query (see
    :func:`~smarter.lib.annotation.models.prefetch_annotations`).
    """

    model: ClassVar[type[models.Model]]
    """The resource, whose manager ``objects`` is an :class:`OwnershipManager`, e.g. a MetaDataWithOwnershipModel."""

    serializer_class: ClassVar[type[serializers.BaseSerializer]]
    """The serializer of the list's resources."""

    listview_cache_kind: ClassVar[str]
    """The list's name in the cache, as :func:`connect_listview_cache` invalidates it, e.g. ``LLMClient``."""

    sort_fields: ClassVar[Mapping[str, str]] = DEFAULT_SORT_FIELDS
    """The columns that the list may be sorted by.

    See :func:`~smarter.lib.django.pagination.paginate_queryset`.
    """

    search_fields: ClassVar[Sequence[str]] = DEFAULT_SEARCH_FIELDS
    """The fields that a search matches."""

    filters: ClassVar[Optional[Mapping[str, Q]]] = None
    """The list's named filters, if it has any."""

    listview_label: ClassVar[Optional[str]] = None
    """The list's name, where it is shown outside its page, e.g. by the dashboard's search.

    Its model's plural verbose name, by default.
    """

    select_related: ClassVar[tuple[str, ...]] = ()
    """The forward relations that the serializer reads, besides the owner's."""

    prefetch_related: ClassVar[tuple[Union[str, Prefetch], ...]] = ()
    """The reverse and many-to-many relations that the serializer reads, besides the tags."""

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        return f"{self.formatted_text(self.__class__.__module__)}.{self.__class__.__name__}[{id(self)}]"

    @classmethod
    def view_path(cls) -> str:
        """Return the class's dotted path, by which :func:`cached_listview_page` imports it."""
        return f"{cls.__module__}.{cls.__qualname__}"

    @classmethod
    def get_queryset(cls, user: User, ownership_filter: str) -> models.QuerySet:
        """
        Return the resources of the list that the user may see, with the relations that the serializer reads.

        :param user: The authenticated user.
        :param ownership_filter: ``owned``, ``shared`` or ``all``.
        :returns: The resources, newest first.
        """
        manager: OwnershipManager = getattr(cls.model, "objects")
        if ownership_filter == SmarterResourceOwnershipFilterEnum.OWNED:
            queryset = manager.owned_by(user)
        elif ownership_filter == SmarterResourceOwnershipFilterEnum.SHARED:
            queryset = manager.shared_with(user)
        else:
            queryset = manager.with_read_permission_for(user)
        # every MetaDataWithOwnershipModel has an owner and tags, but e.g. SmarterAuthToken has no tags.
        owner_relations = [lookup for lookup in LISTVIEW_OWNER_RELATIONS if has_field(cls.model, lookup)]
        tags = ["tags"] if _is_relation(cls.model, "tags") else []
        return (
            queryset.select_related(*owner_relations, *cls.select_related)
            .prefetch_related(*tags, *cls.prefetch_related)
            .order_by("-updated_at")
        )

    @classmethod
    def build_page(  # pylint: disable=R0913,R0914,R0917
        cls,
        user_profile,
        ownership_filter: str,
        page: Optional[str] = None,
        page_size: Optional[str] = None,
        search: str = "",
        ordering: str = "",
        list_filter: str = "",
        tags: Sequence[str] = (),
        annotations: Sequence[str] = (),
    ) -> SmarterDictType:
        """
        Build one page of the list api's response, from the database.

        The serializer gets a :class:`ListviewPageRequest`, whose user is the user profile's.
        The result is passed through JSON, so that the cache stores plain values, not the
        serializer's ``ReturnDict``, which refers to the serializer.

        :param user_profile: The authenticated user's UserProfile.
        :param ownership_filter: ``owned``, ``shared`` or ``all``.
        :param page: The ``page`` query parameter.
        :param page_size: The ``page_size`` query parameter.
        :param search: The ``search`` query parameter.
        :param ordering: The ``ordering`` query parameter.
        :param list_filter: The ``filter`` query parameter.
        :param tags: Tags that every resource must have.
        :param annotations: An annotation selector's requirements, e.g. ``acme.com/crm-id=A-1``.
        :returns: ``{"user": ..., "admin": ..., "objects": [...], "pagination": {...}}``.
        """
        # pylint: disable=C0415
        from smarter.apps.account.serializers import UserProfileSerializer
        from smarter.apps.account.utils import smarter_cached_objects
        from smarter.lib.annotation.models import prefetch_annotations

        objects, pagination = paginate_queryset(
            cls.get_queryset(user_profile.user, ownership_filter),
            page=page,
            page_size=page_size,
            search=search,
            ordering=ordering,
            list_filter=list_filter,
            search_fields=cls.search_fields,
            sort_fields=cls.sort_fields,
            filters=cls.filters,
            tags=tags,
            annotations=annotations,
        )
        # the serializer shows each resource's annotations, which aren't a relation to prefetch.
        prefetch_annotations(objects)
        request = ListviewPageRequest(user_profile.user)
        response = {
            "user": UserProfileSerializer(user_profile).data,
            "admin": UserProfileSerializer(smarter_cached_objects.smarter_admin_user_profile).data,
            "objects": cls.serializer_class(objects, many=True, context={"request": request}).data,
            "pagination": pagination,
        }
        return json.loads(json.dumps(response, cls=DjangoJSONEncoder))

    def get(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """Return the same json as a POST, so that the list api can be browsed."""
        return self.post(request, *args, **kwargs)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:  # pylint: disable=W0613
        """
        Return one page of the list's resources, which the user owns, are shared with them, or both.

        :param request: The request. Its query parameters are ``page``, ``page_size``, ``search``,
            ``ordering``, ``filter``, ``tag`` and ``annotation`` (both repeatable) and
            ``invalidate_cache``, all optional.
        :param kwargs: ``ownership_filter``, from the url: ``owned``, ``shared`` or ``all`` (the default).
        :returns: The page, or a 400 response for an unknown ownership filter.
        """
        ownership_filter = kwargs.get("ownership_filter") or SmarterResourceOwnershipFilterEnum.ALL
        if ownership_filter not in OWNERSHIP_FILTERS:
            logger.warning(
                "%s.post() Received an invalid ownership_filter value: %s. Must be one of 'owned', 'shared', or 'all'.",
                self.formatted_class_name,
                ownership_filter,
            )
            return JsonResponse(
                {"error": "Invalid ownership_filter. Must be one of 'owned', 'shared', or 'all'."},
                status=HTTPStatus.BAD_REQUEST,
            )

        kind = self.listview_cache_kind
        user_profile_id = self.user_profile.id  # type: ignore[union-attr]
        if request.GET.get("invalidate_cache", "false").lower() == "true":
            listview_cache_generation.invalidate(kind, user_profile_id)

        logger.debug(
            "%s.post() ownership_filter=%s, query=%s, user_profile=%s",
            self.formatted_class_name,
            ownership_filter,
            request.GET.dict(),
            user_profile_id,
        )
        response = cached_listview_page(
            self.view_path(),
            kind_generation=listview_cache_generation(kind, None),
            user_generation=listview_cache_generation(kind, user_profile_id),
            all_generation=listview_cache_generation(LISTVIEW_CACHE_ALL, None),
            user_profile_id=user_profile_id,
            ownership_filter=ownership_filter,
            page=request.GET.get("page"),
            page_size=request.GET.get("page_size"),
            search=request.GET.get("search", ""),
            ordering=request.GET.get("ordering", ""),
            list_filter=request.GET.get("filter", ""),
            # tuples of plain strings, so that they are part of the page's cache key.
            tags=clean_query_values(request.GET.getlist("tag"), MAX_LIST_TAGS),
            annotations=clean_query_values(request.GET.getlist("annotation"), MAX_LIST_ANNOTATIONS),
        )
        return JsonResponse(response)


LISTVIEW_PAGE_SUFFIX = "ListView"
"""The suffix of the class name of a list's console page, e.g. GuardrailListView."""


class ListviewEntry(NamedTuple):
    """A list of the web console: its list api, and the url of its console page."""

    view_class: type["SmarterListApiView"]
    """The list api, e.g. GuardrailListApiView."""

    page_url: str
    """The path of the list's console page, e.g. ``/guardrail/``."""

    @property
    def label(self) -> str:
        """The list's name: the list api's :attr:`~SmarterListApiView.listview_label`, or its model's plural verbose name."""
        model = self.view_class.model
        return self.view_class.listview_label or str(model._meta.verbose_name_plural)  # pylint: disable=W0212


def _is_page_view(view_class) -> bool:
    """Whether a view is a list's console page: a ``...ListView`` that is not a list api."""
    return (
        isinstance(view_class, type)
        and view_class.__name__.endswith(LISTVIEW_PAGE_SUFFIX)
        and not issubclass(view_class, SmarterListApiView)
    )


def _walk_listviews(patterns, namespaces: tuple[str, ...] = ()):
    """
    Yield each list api of ``patterns``, the url name of its console page, and how deeply it is included.

    The page is the ``...ListView`` of the same urlconf whose name matches the api's, e.g.
    GuardrailListView for GuardrailListApiView, or else the urlconf's first ``...ListView``. Its name
    is joined with its namespaces, e.g. ``guardrail:guardrail_list_view``.
    """
    pages = {
        view_class.__name__: pattern.name
        for pattern in patterns
        if isinstance(pattern, URLPattern)
        and pattern.name
        and _is_page_view(view_class := getattr(pattern.callback, "view_class", None))
    }
    for pattern in patterns:
        if isinstance(pattern, URLResolver):
            namespace = (pattern.namespace,) if pattern.namespace else ()
            yield from _walk_listviews(pattern.url_patterns, namespaces + namespace)
        elif isinstance(pattern, URLPattern) and pages:
            view_class = getattr(pattern.callback, "view_class", None)
            if isinstance(view_class, type) and issubclass(view_class, SmarterListApiView):
                page_class = view_class.__name__.replace("ListApiView", LISTVIEW_PAGE_SUFFIX)
                page = pages.get(page_class) or next(iter(pages.values()))
                yield view_class, ":".join(namespaces + (page,)), len(namespaces)


@functools.cache
def listview_registry() -> tuple[ListviewEntry, ...]:
    """
    Return every list of the web console, found in the root urlconf, once per list api.

    A list is a list api (a :class:`SmarterListApiView`) and the console page whose urlconf
    routes it, a view whose class name ends with ``ListView``. A urlconf that is included more than
    once, e.g. the plugins' under ``/llm-tools/`` and under the dashboard, gives the page of its
    shallowest inclusion, which the sidebar links to too. The urlconf doesn't change while the
    process runs, so the registry is computed once per process.

    :returns: The lists, in the urlconf's order.
    """
    pages: dict[type[SmarterListApiView], tuple[int, str]] = {}
    for view_class, page_name, depth in _walk_listviews(get_resolver().url_patterns):
        if view_class not in pages or depth < pages[view_class][0]:
            pages[view_class] = (depth, page_name)
    retval: list[ListviewEntry] = []
    for view_class, (_, page_name) in pages.items():
        try:
            retval.append(ListviewEntry(view_class=view_class, page_url=django_reverse(page_name)))
        except NoReverseMatch:
            logger.warning("%s.listview_registry() can't reverse %s's page %s", logger_prefix, view_class, page_name)
    return tuple(retval)


__all__ = [
    "LISTVIEW_CACHE_ALL",
    "LISTVIEW_PAGE_SUFFIX",
    "ListviewEntry",
    "ListviewPageRequest",
    "SmarterListApiView",
    "cached_listview_page",
    "connect_listview_cache",
    "invalidate_listview_cache",
    "listview_cache_generation",
    "listview_registry",
]
