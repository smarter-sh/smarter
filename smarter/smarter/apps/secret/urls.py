"""URL configuration for the web platform."""

from django.urls import path

from smarter.apps.secret.views.dashboard.secrets import SecretsView, SecretView
from smarter.common.utils import camel_case_object_name

from .const import namespace


class SecretReverseNames:
    """
    Holds named URL patterns for the account dashboard.
    This class provides constants for all named URL patterns used in the account dashboard views.
    The names follow the convention: 'dashboard_account_<view_name>'.
    These are referenced in Django templates as 'reverse' or 'url' tags.

    .. usage-example::

      .. html::

      <a href="{% url 'dashboard_account_dashboard_overview' %}">Go to Dashboard Overview</a>

    """

    namespace = namespace

    SECRETS = camel_case_object_name(SecretsView)
    SECRET = camel_case_object_name(SecretView)
    SECRET_NEW = camel_case_object_name(SecretView) + "_new"


app_name = namespace

urlpatterns = [
    path("", SecretsView.as_view(), name=SecretReverseNames.SECRETS),
    path("new/", SecretView.as_view(), name=SecretReverseNames.SECRET_NEW),
    path("<int:secret_id>/", SecretView.as_view(), name=SecretReverseNames.SECRET),
]
