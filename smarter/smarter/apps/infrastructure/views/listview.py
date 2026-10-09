# pylint: disable=W0613
"""
Views of the React Infrastructure Resource list in the Smarter web console.

The ledger, :class:`~smarter.apps.infrastructure.models.InfrastructureResource`, describes the
platform's cloud infrastructure and what it costs, so it is for superusers only. It is written
by the infrastructure signals' receivers, so the list is read-only.
"""

from http import HTTPStatus
from typing import Any, Optional

from django.conf import settings
from django.core.handlers.asgi import ASGIRequest
from django.core.paginator import Paginator
from django.db.models import Count, Q, QuerySet
from django.http import JsonResponse
from django.shortcuts import render

from smarter.lib import json, logging
from smarter.lib.django.http.shortcuts import SmarterHttpResponseForbidden
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active

from ..models import InfrastructureResource
from ..serializers import InfrastructureResourceSerializer

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.INFRASTRUCTURE_LOGGING])

DEFAULT_PAGE_SIZE = 50
"""The resources of a page, unless the list asks for another number."""

MAX_PAGE_SIZE = 500
"""The most resources that a page may have."""


FORBIDDEN = "Only superusers may see the platform's infrastructure resources."


def summary() -> dict[str, int]:
    """Counts of the ledger's resources: in total, active, active and billable, and destroyed."""
    active = Q(status=InfrastructureResource.Status.ACTIVE)
    return InfrastructureResource.objects.aggregate(
        total=Count("id"),
        active=Count("id", filter=active),
        activeBillable=Count("id", filter=active & Q(billable=True)),
        destroyed=Count("id", filter=Q(status=InfrastructureResource.Status.DESTROYED)),
    )


def filter_resources(body: dict[str, Any]) -> QuerySet[InfrastructureResource]:
    """
    The ledger's resources that match the list's filters, newest first.

    :param body: The list's request, whose filters are optional: ``status``, ``active``,
        ``destroyed`` or ``all``; ``billableOnly``; ``provider``; ``resourceType``, e.g.
        ``kubernetes.node``; and ``text``, which the resource's name, type, id or service contains.
    :returns: The matching resources.
    """
    qs = InfrastructureResource.objects.order_by("-created_at", "-id")
    status = body.get("status")
    if status in InfrastructureResource.Status.values:
        qs = qs.filter(status=status)
    if body.get("billableOnly") is True:
        qs = qs.filter(billable=True)
    for key, field in (("provider", "provider"), ("resourceType", "resource_type")):
        value = body.get(key)
        if isinstance(value, str) and value:
            qs = qs.filter(**{field: value})
    text = body.get("text")
    if isinstance(text, str) and text.strip():
        text = text.strip()
        qs = qs.filter(
            Q(resource_name__icontains=text)
            | Q(resource_type__icontains=text)
            | Q(resource_id__icontains=text)
            | Q(service__icontains=text)
        )
    return qs


def choices() -> dict[str, list[str]]:
    """The providers and resource types of the whole ledger, for the list's filters."""

    def distinct(field: str) -> list[str]:
        return list(InfrastructureResource.objects.order_by(field).values_list(field, flat=True).distinct())

    return {"providers": distinct("provider"), "resourceTypes": distinct("resource_type")}


def positive_int(value: Any, default: int, maximum: Optional[int] = None) -> int:
    """An integer of the request, from 1 up to ``maximum``, if any, or else ``default``."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return default
    if maximum is not None and value > maximum:
        return default
    return value


class InfrastructureResourceListView(SmarterAuthenticatedNeverCachedWebView):
    """Render the Infrastructure Resource list of the Smarter web console."""

    template_path = "react/infrastructure-resource-list.html"

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        return self.formatted_text(f"{__name__}.{InfrastructureResourceListView.__name__}[{id(self)}]")

    def get(self, request: ASGIRequest, *args, **kwargs):
        if not request.user.is_superuser:  # type: ignore[union-attr]
            return SmarterHttpResponseForbidden(request=request, error_message=FORBIDDEN)

        # pylint: disable=C0415
        from ..urls import InfrastructureReverseNames

        context = {
            "infrastructure_resource_list": {
                "root_id": "smarter-infrastructure-resource-list-root",
                "django_csrf_cookie_name": settings.CSRF_COOKIE_NAME,
                "django_session_cookie_name": settings.SESSION_COOKIE_NAME,
                "cookie_domain": settings.SESSION_COOKIE_DOMAIN,
                "infrastructure_resource_list_api_url": reverse(
                    InfrastructureReverseNames.namespace, InfrastructureReverseNames.listview_api
                ),
                "react_debug_mode": switch_is_active(SmarterWaffleSwitches.ENABLE_REACTAPP_DEBUG_MODE),
                "smarter_request_id": self.generate_smarter_request_id(),
            }
        }
        return render(request, template_name=self.template_path, context=context)


class InfrastructureResourceListApiView(SmarterAuthenticatedNeverCachedWebView):
    """
    A page of the ledger's resources that match the list's filters, newest first, and a summary of all of them.

    The request's JSON body may have the filters of :func:`filter_resources`, and ``page``, from
    1, and ``pageSize``, up to :data:`MAX_PAGE_SIZE`. A page past the last is the last.

    **Response**::

        {
            "summary": {"total": 12, "active": 9, "activeBillable": 3, "destroyed": 3},
            "objects": [{"id": 12, "provider": "aws", "resourceType": "dns.zone", ...}],
            "pagination": {"page": 1, "pageSize": 50, "numPages": 1, "count": 9},
            "choices": {"providers": ["aws"], "resourceTypes": ["dns.record", "dns.zone"]}
        }
    """

    @property
    def formatted_class_name(self) -> str:
        return self.formatted_text(f"{__name__}.{InfrastructureResourceListApiView.__name__}[{id(self)}]")

    def post(self, request: ASGIRequest, *args, **kwargs) -> JsonResponse:
        if not request.user.is_superuser:  # type: ignore[union-attr]
            return JsonResponse({"error": FORBIDDEN}, status=HTTPStatus.FORBIDDEN)
        try:
            body = json.loads(request.body or b"{}")
        except json.JSONDecodeError:
            body = {}
        if not isinstance(body, dict):
            body = {}
        page_size = positive_int(body.get("pageSize"), DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE)
        paginator = Paginator(filter_resources(body), page_size)
        # get_page() returns the last page for a page past it.
        page = paginator.get_page(positive_int(body.get("page"), 1))
        retval = {
            "summary": summary(),
            "objects": InfrastructureResourceSerializer(page.object_list, many=True).data,
            "pagination": {
                "page": page.number,
                "pageSize": page_size,
                "numPages": paginator.num_pages,
                "count": paginator.count,
            },
            "choices": choices(),
        }
        logger.debug("%s.post() returning %s resources", self.formatted_class_name, len(retval["objects"]))
        return JsonResponse(retval)


__all__ = [
    "InfrastructureResourceListApiView",
    "InfrastructureResourceListView",
    "choices",
    "filter_resources",
    "summary",
]
