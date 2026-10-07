"""
URL configuration for the Proxy passthrough.

These are mounted at ``/api/v1/proxy/``, if ``SMARTER_ENABLE_PROXY`` is true. See
:mod:`smarter.apps.proxy.api.v1.views`.
"""

from django.urls import path

from smarter.common.utils import to_snake_case

from .const import namespace
from .views import ProxyListView, ProxyPassthroughView

app_name = namespace


class ProxyApiV1ReverseViews:
    """
    Reverse view names for the Proxy passthrough.

    Example
    -------
    .. code-block:: python

        from django.urls import reverse
        url = reverse(
            f"{ProxyApiV1ReverseViews.namespace}:{ProxyApiV1ReverseViews.passthrough}",
            kwargs={"name": "openai", "path": "chat/completions"},
        )
    """

    namespace = "api:v1:proxy"

    list_view = to_snake_case(ProxyListView.__name__)
    passthrough = to_snake_case(ProxyPassthroughView.__name__)
    passthrough_root = to_snake_case(ProxyPassthroughView.__name__) + "_root"


urlpatterns = [
    path("", ProxyListView.as_view(), name=ProxyApiV1ReverseViews.list_view),
    path("<str:name>/", ProxyPassthroughView.as_view(), name=ProxyApiV1ReverseViews.passthrough_root),
    path("<str:name>/<path:path>", ProxyPassthroughView.as_view(), name=ProxyApiV1ReverseViews.passthrough),
]
