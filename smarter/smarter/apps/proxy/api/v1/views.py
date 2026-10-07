# pylint: disable=W0613
"""
Proxy api/v1/proxy views: the Proxy passthrough.

- ``GET proxy/``: the Proxies that the caller may use.
- ``<METHOD> proxy/<name>/<path>``: forward the request to the Proxy's provider, at
  ``<baseUrl><path>``, with the provider's API key, and return the provider's response.

The caller authenticates with a Smarter API key, in any of the headers that LLM SDKs use. See
:mod:`smarter.apps.proxy.authentication`.
"""

from django.http import JsonResponse
from django.http.response import HttpResponseBase
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.views import APIView

from smarter.apps.account.models import UserProfile
from smarter.apps.proxy.authentication import SmarterProxyAuthentication
from smarter.apps.proxy.exceptions import ProxyError
from smarter.apps.proxy.services import ProxyForwarder, proxies_for, resolve_proxy
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROXY_LOGGING])


class ProxyApiViewBase(APIView):
    """
    Base class of the Proxy passthrough's views.

    Only a Smarter API key authenticates: the web console's session does not, so that the
    passthrough is not exposed to cross-site requests.
    """

    authentication_classes = [SmarterProxyAuthentication]
    permission_classes = [IsAuthenticated]

    def get_user_profile(self, request: Request) -> UserProfile:
        return UserProfile.get_cached_object(user=request.user)  # type: ignore[arg-type]


class ProxyListView(ProxyApiViewBase):
    """The Proxies that the caller may use, with their URLs."""

    def get(self, request: Request, *args, **kwargs):
        user_profile = self.get_user_profile(request)
        proxies = [
            {
                "name": proxy.name,
                "description": proxy.description,
                "provider": proxy.provider.name,
                "url": request.build_absolute_uri(proxy.url),
                "upstreamUrl": proxy.upstream_base_url,
                "allowedPaths": proxy.allowed_paths or [],
                "isActive": proxy.is_active,
            }
            for proxy in proxies_for(user_profile).order_by("name")
        ]
        return JsonResponse({"proxies": proxies})


class ProxyPassthroughView(ProxyApiViewBase):
    """
    Forward a request to a Proxy's provider, and return its response, as it is.

    Errors of Smarter's own, e.g. an unknown Proxy, are JSON, in the shape that the OpenAI and
    Anthropic SDKs report: ``{"error": {"message": ..., "type": "smarter_proxy_error", "code": ...}}``.
    """

    # HEAD is handled by get(), as Django does for every view.
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def passthrough(self, request: Request, name: str, path: str = "") -> HttpResponseBase:
        try:
            user_profile = self.get_user_profile(request)
            proxy = resolve_proxy(name, user_profile)
            return ProxyForwarder(proxy, user_profile).forward(
                method=request.method or "GET",
                path=path,
                query_string=request.META.get("QUERY_STRING", ""),
                headers=request.headers,
                body=request.body,
            )
        except ProxyError as e:
            return JsonResponse(e.to_dict(), status=e.status)

    def get(self, request: Request, name: str, path: str = "", *args, **kwargs):
        return self.passthrough(request, name, path)

    def post(self, request: Request, name: str, path: str = "", *args, **kwargs):
        return self.passthrough(request, name, path)

    def put(self, request: Request, name: str, path: str = "", *args, **kwargs):
        return self.passthrough(request, name, path)

    def patch(self, request: Request, name: str, path: str = "", *args, **kwargs):
        return self.passthrough(request, name, path)

    def delete(self, request: Request, name: str, path: str = "", *args, **kwargs):
        return self.passthrough(request, name, path)


__all__ = ["ProxyListView", "ProxyPassthroughView"]
