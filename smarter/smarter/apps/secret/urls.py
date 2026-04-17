"""URL configuration for the web platform."""

from django.urls import include, path

from smarter.apps.secret.api import urls as api_urls
from smarter.apps.secret.views.dashboard import urls as dashboard_urls

from .const import namespace


class SecretNamedUrls:
    """
    Class to hold named URL patterns for the secret app.
    This class provides constants for all named URL patterns used in the secret dashboard views.
    The names follow the convention: 'secret_<view_name>'.
    These are referenced in Django templates as 'reverse' or 'url' tags.

    .. usage-example::

      .. html::

      <a href="{% url 'dashboard_secret_dashboard_overview' %}">Go to Dashboard Overview</a>

    """

    namespace = namespace


app_name = namespace

urlpatterns = [
    path("", include(dashboard_urls)),
    path("api/", include(api_urls)),
]
