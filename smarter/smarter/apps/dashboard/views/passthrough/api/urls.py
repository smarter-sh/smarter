"""
URL configuration for the Prompt Passthrough's endpoints in the web console's api.

These are mounted at ``/api/web/dashboard/passthrough/``, from
:mod:`smarter.apps.dashboard.api.web.urls`. Registration is conditional on the
``ENABLE_DASHBOARD_PASSTHROUGH_PROMPT`` setting, as is the Prompt Passthrough page's: when
disabled, no routes are registered.

These endpoints are part of Smarter's Django-React integration. The Django view that renders a
console page reverses their urls and passes them to the page's React app, in the attributes of
its root element, and the app calls them with the browser's Django session and CSRF token. See
:doc:`/smarter-framework/developer-reference/react-integration`.
"""

from django.urls import path

from smarter.apps.api.web.const import path_namespace
from smarter.apps.dashboard.const import namespace as dashboard_namespace
from smarter.apps.dashboard.views.passthrough.api.providers import ProviderApiView
from smarter.apps.dashboard.views.passthrough.const import namespace
from smarter.common.conf import smarter_settings
from smarter.common.utils.conversion import to_snake_case

app_name = namespace


class PassthroughApiReverseNames:
    """
    Reverse view names for the Prompt Passthrough's endpoints in the web console's api.

    Example
    -------
    .. code-block:: python

        from smarter.lib.django.shortcuts import reverse

        url = reverse(PassthroughApiReverseNames.namespace, PassthroughApiReverseNames.api_providers)
    """

    namespace = f"{path_namespace}:{dashboard_namespace}:{namespace}"

    api_providers = to_snake_case(ProviderApiView.__name__)


urlpatterns = []

if smarter_settings.enable_dashboard_passthrough_prompt:
    urlpatterns = [
        path("providers/", ProviderApiView.as_view(), name=PassthroughApiReverseNames.api_providers),
    ]
