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
from smarter.apps.proxy.contract.models import ProxyApiProxies, ProxyApiProxy
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
        """
        Return the authenticated user's profile, from the cache.

        :param request: The authenticated request.
        :returns: The user's UserProfile.
        """
        return UserProfile.get_cached_object(user=request.user)  # type: ignore[arg-type]


class ProxyListView(ProxyApiViewBase):
    """The Proxies that the caller may use, with their URLs."""

    def get(self, request: Request, *args, **kwargs):
        """
        Return the Proxies that the caller may use, ordered by name.

        :param request: The authenticated request.
        :returns: A :class:`ProxyApiProxies` document, as JSON.
        """
        user_profile = self.get_user_profile(request)
        usable_proxies = proxies_for(user_profile).order_by("name")
        proxies = [ProxyApiProxy.from_model(proxy, request) for proxy in usable_proxies]
        return JsonResponse(ProxyApiProxies(proxies=proxies).model_dump(mode="json"))


class ProxyPassthroughView(ProxyApiViewBase):
    """
    Forward a request to a Proxy's provider, and return its response, as it is.

    Errors of Smarter's own, e.g. an unknown Proxy, are JSON, in the shape that the OpenAI and
    Anthropic SDKs report: ``{"error": {"message": ..., "type": "smarter_proxy_error", "code": ...}}``.
    """

    # HEAD is handled by get(), as Django does for every view.
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def passthrough(self, request: Request, name: str, path: str = "") -> HttpResponseBase:
        """
        Forward the request to the named Proxy's provider, and return the provider's response.

        :param request: The authenticated request, whose method, query string, headers and body are
            forwarded.
        :param name: The Proxy's name, from the url.
        :param path: The provider API path after the Proxy's name, from the url.
        :returns: The provider's response, or a JSON error response when the Proxy cannot be resolved
            or the forward fails with a :class:`ProxyError`.
        """
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
        """
        Forward a GET request: see :meth:`passthrough`.

        :param request: The request.
        :param name: The Proxy's name.
        :param path: The provider API path.
        :returns: The provider's response.
        """
        return self.passthrough(request, name, path)

    def post(self, request: Request, name: str, path: str = "", *args, **kwargs):
        """
        Forward a POST request: see :meth:`passthrough`.

        :param request: The request.
        :param name: The Proxy's name.
        :param path: The provider API path.
        :returns: The provider's response.
        """
        return self.passthrough(request, name, path)

    def put(self, request: Request, name: str, path: str = "", *args, **kwargs):
        """
        Forward a PUT request: see :meth:`passthrough`.

        :param request: The request.
        :param name: The Proxy's name.
        :param path: The provider API path.
        :returns: The provider's response.
        """
        return self.passthrough(request, name, path)

    def patch(self, request: Request, name: str, path: str = "", *args, **kwargs):
        """
        Forward a PATCH request: see :meth:`passthrough`.

        :param request: The request.
        :param name: The Proxy's name.
        :param path: The provider API path.
        :returns: The provider's response.
        """
        return self.passthrough(request, name, path)

    def delete(self, request: Request, name: str, path: str = "", *args, **kwargs):
        """
        Forward a DELETE request: see :meth:`passthrough`.

        :param request: The request.
        :param name: The Proxy's name.
        :param path: The provider API path.
        :returns: The provider's response.
        """
        return self.passthrough(request, name, path)


__all__ = ["ProxyListView", "ProxyPassthroughView"]
