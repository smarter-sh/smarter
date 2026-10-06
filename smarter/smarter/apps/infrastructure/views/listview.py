# pylint: disable=W0613
"""
Views of the React Infrastructure Resource list in the Smarter web console.

The ledger, :class:`~smarter.apps.infrastructure.models.InfrastructureResource`, describes the
platform's cloud infrastructure and what it costs, so it is for superusers only. It is written
by the infrastructure signals' receivers, so the list is read-only.
"""

from http import HTTPStatus

from django.conf import settings
from django.core.handlers.asgi import ASGIRequest
from django.db.models import Count, Q
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

DEFAULT_LIMIT = 1000
"""The most recent resources that the list returns, unless it asks for fewer."""

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
    The ledger's most recent resources, newest first, and a summary of all of them.

    The request's JSON body may have ``limit``, the number of resources, up to :data:`DEFAULT_LIMIT`.

    **Response**::

        {
            "summary": {"total": 12, "active": 9, "activeBillable": 3, "destroyed": 3},
            "objects": [{"id": 12, "provider": "aws", "resourceType": "dns.zone", ...}]
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
        limit = body.get("limit") if isinstance(body, dict) else None
        if not isinstance(limit, int) or not 0 < limit <= DEFAULT_LIMIT:
            limit = DEFAULT_LIMIT
        resources = InfrastructureResource.objects.order_by("-created_at", "-id")[:limit]
        retval = {
            "summary": summary(),
            "objects": InfrastructureResourceSerializer(resources, many=True).data,
        }
        logger.debug("%s.post() returning %s resources", self.formatted_class_name, len(retval["objects"]))
        return JsonResponse(retval)


__all__ = ["InfrastructureResourceListApiView", "InfrastructureResourceListView", "summary"]
