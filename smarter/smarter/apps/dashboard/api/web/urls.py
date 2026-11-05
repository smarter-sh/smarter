"""
URL configuration for the Dashboard app's endpoints in the web console's api.

These are mounted at ``/api/web/dashboard/``, and the dashboard's React apps call them. Each
group of endpoints keeps its own urls module and ``ReverseNames`` class, whose ``namespace`` is
its full path from the root urlconf:

- ``""`` — the dashboard's widgets, the welcome dialog, the onboarding hints, global search and
  the resource detail api. See :mod:`smarter.apps.dashboard.views.views.api.urls`
  (``api:web:dashboard``).
- ``"passthrough/"`` — the Prompt Passthrough's providers. See
  :mod:`smarter.apps.dashboard.views.passthrough.api.urls` (``api:web:dashboard:passthrough``).
- ``"logs/"`` — the server log stream. See :mod:`smarter.apps.dashboard.views.terminal_emulator.urls`
  (``api:web:dashboard:logs``).
- ``"terminal/"`` — the Terminal's ticket api. See
  :mod:`smarter.apps.dashboard.views.terminal_emulator.api.urls` (``api:web:dashboard:terminal``).

The passthrough and logs modules register no routes while their feature is disabled. The Manifest
Drop Zone has no endpoint of its own: it applies manifests with the public api's
``/api/v1/cli/apply/``. See :mod:`smarter.apps.api.web`.

These endpoints are part of Smarter's Django-React integration. The Django view that renders a
console page reverses their urls and passes them to the page's React app, in the attributes of
its root element, and the app calls them with the browser's Django session and CSRF token. See
:doc:`/smarter-framework/developer-reference/react-integration`.
"""

from django.urls import include, path

from smarter.apps.dashboard.const import namespace
from smarter.apps.dashboard.views.passthrough.api import urls as passthrough_api_urls
from smarter.apps.dashboard.views.terminal_emulator import urls as logs_api_urls
from smarter.apps.dashboard.views.terminal_emulator.api import urls as terminal_api_urls
from smarter.apps.dashboard.views.views.api import urls as dashboard_api_urls

app_name = namespace


urlpatterns = [
    path("", include(dashboard_api_urls)),
    path("passthrough/", include(passthrough_api_urls, namespace=passthrough_api_urls.app_name)),
    path("logs/", include(logs_api_urls, namespace=logs_api_urls.app_name)),
    path("terminal/", include(terminal_api_urls, namespace=terminal_api_urls.app_name)),
]
