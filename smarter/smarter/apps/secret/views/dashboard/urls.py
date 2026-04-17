"""URL configuration for the web platform."""

from django.urls import path

from smarter.apps.secret.views.dashboard.secrets import SecretsView, SecretView


class DashboardNamedUrls:
    """
    Holds named URL patterns for the account dashboard.
    This class provides constants for all named URL patterns used in the account dashboard views.
    The names follow the convention: 'dashboard_account_<view_name>'.
    These are referenced in Django templates as 'reverse' or 'url' tags.

    .. usage-example::

      .. html::

      <a href="{% url 'dashboard_account_dashboard_overview' %}">Go to Dashboard Overview</a>

    """

    SECRETS = "dashboard_secrets"
    SECRET = "dashboard_secret"
    SECRET_NEW = "dashboard_secret_new"


urlpatterns = [
    path("", SecretsView.as_view(), name=DashboardNamedUrls.SECRETS),
    path("new/", SecretView.as_view(), name=DashboardNamedUrls.SECRET_NEW),
    path("<int:secret_id>/", SecretView.as_view(), name=DashboardNamedUrls.SECRET),
]
