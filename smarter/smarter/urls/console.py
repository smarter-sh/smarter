"""
URLs for Smarter web console.
"""

import logging
import sys

from django.apps import apps
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.admin.exceptions import AlreadyRegistered
from django.contrib.admindocs import urls as admindocs_urls
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.generic.base import RedirectView
from django.views.static import serve
from social_django import urls as social_django_urls
from waffle import get_waffle_switch_model

from smarter.apps.account import urls as account_urls
from smarter.apps.account.const import namespace as account_namespace
from smarter.apps.account.urls import AccountNamedUrls
from smarter.apps.account.views.authentication import (
    AccountRegisterView,
    LoginView,
    LogoutView,
)
from smarter.apps.account.views.password_management import (
    PasswordConfirmView,
    PasswordResetRequestView,
    PasswordResetView,
)
from smarter.apps.api import api_urls
from smarter.apps.api import console_urls as api_drop_zone_urls
from smarter.apps.api.const import console_namespace as api_console_namespace
from smarter.apps.api.const import namespace as api_namespace
from smarter.apps.chatbot.api.v1.views.default import DefaultChatbotApiView
from smarter.apps.connection import urls as connection_urls
from smarter.apps.connection.const import namespace as connection_namespace
from smarter.apps.dashboard import urls as dashboard_urls
from smarter.apps.dashboard.admin import (
    SmarterSuperUserOnlyModelAdmin,
    smarter_restricted_admin_site,
)
from smarter.apps.dashboard.const import namespace as dashboard_namespace
from smarter.apps.docs import urls as docs_urls
from smarter.apps.docs.const import namespace as docs_namespace
from smarter.apps.docs.views.webserver import (
    FaviconView,
    HealthzView,
    ReadinessView,
    RobotsTxtView,
    SitemapXmlView,
)
from smarter.apps.plugin import urls as plugin_urls
from smarter.apps.plugin.const import namespace as plugin_namespace
from smarter.apps.prompt import urls as prompt_urls
from smarter.apps.prompt.const import namespace as prompt_workbench_namespace
from smarter.apps.prompt.views.views import ChatConfigView
from smarter.apps.provider import urls as provider_urls
from smarter.apps.provider.const import namespace as provider_namespace
from smarter.apps.secret import urls as secret_urls
from smarter.apps.secret.const import namespace as secret_namespace
from smarter.apps.vectorstore import urls as vectorstore_urls
from smarter.apps.vectorstore.const import namespace as vectorstore_namespace
from smarter.common.conf import smarter_settings
from smarter.common.const import SmarterEnvironments
from smarter.common.helpers.logger_helpers import formatted_text
from smarter.lib.django.waffle import SmarterSwitchAdmin

logger = logging.getLogger(__name__)


def session_test_view(request):
    """
    Deprecated?
    """
    request.session["test_key"] = "test_value"
    request.session.modified = True  # Ensure session is saved
    return JsonResponse({"session_key": request.session.session_key, "test_key": request.session.get("test_key")})


# -----------------------------------------------------------------------------
# Initialize custom admin site for Smarter
# -----------------------------------------------------------------------------
admin.site = smarter_restricted_admin_site
admin.autodiscover()

Switch = get_waffle_switch_model()
"""
Add a custom admin site that is accessible to staff users, but excludes
superuser-only models.
"""
smarter_restricted_admin_site.register(Switch, SmarterSwitchAdmin)

EXCLUDED_MODELS = [
    "knox.AuthToken",  # We have our own admin for this
    "waffle.Switch",
    "waffle.Sample",
    "waffle.Flag",
]
"""
superuser-only models to exclude from registration with
smarter_restricted_admin_site, which is accessible to staff users.
"""

SMARTER_APP_LABELS = [
    "account",
    "api",
    "chatbot",
    "plugin",
    "prompt",
    "provider",
    "vectorstore",
]
"""
app labels that are independently registered at the app level
using the admin module. These are granuarly registered with the
appropriate permission configuration at the app level, so we can skip them here
when we loop through all models for registration with smarter_restricted_admin_site.
"""

# -----------------------------------------------------------------------------
# Register all ORM models with the custom Django admin site. Where necessaary,
# we limit access to superusers only.
# -----------------------------------------------------------------------------
models = apps.get_models()
for model in models:
    # pylint: disable=protected-access
    app_label = model._meta.app_label
    model_label = f"{app_label}.{model._meta.object_name}"

    # Smarter apps that are registered in their respective
    # admin modules.
    if app_label in SMARTER_APP_LABELS:
        continue

    # any other apps that require special handling (see above).
    if model_label in EXCLUDED_MODELS:
        continue

    try:
        # for anything that didn't pass muster, we register with
        # our own "superuser only" model configuration that will
        # limit visibility of the model to superusers only.
        smarter_restricted_admin_site.register(model, SmarterSuperUserOnlyModelAdmin)
    except AlreadyRegistered:
        pass


name_prefix = "console"


urlpatterns = [
    # -----------------------------------
    # root paths
    # -----------------------------------
    path("", RedirectView.as_view(pattern_name="dashboard:dashboard"), name=f"{name_prefix}_home"),
    path("apply/", include(api_drop_zone_urls, namespace=api_console_namespace)),
    path("account/", include(account_urls, namespace=account_namespace)),
    path("admin/docs/", include(admindocs_urls)),
    path("admin/", admin.site.urls, name="django_admin"),
    path("api/", include(api_urls, namespace=api_namespace)),
    path("connection/", include(connection_urls, namespace=connection_namespace)),
    path("dashboard/", include(dashboard_urls, namespace=dashboard_namespace)),
    path("docs/", include(docs_urls, namespace=docs_namespace)),
    path("login/", LoginView.as_view(), name="login_view"),
    path("logout/", LogoutView.as_view(), name="logout_view"),
    path("plugin/", include(plugin_urls, namespace=plugin_namespace)),
    path("provider/", include(provider_urls, namespace=provider_namespace)),
    path("register/", AccountRegisterView.as_view(), name=f"{name_prefix}_register_view"),
    path("session-test/", session_test_view, name="session_test"),
    path("workbench/", include(prompt_urls, namespace=prompt_workbench_namespace)),
    path("secret/", include(secret_urls, namespace=secret_namespace)),
    path("vectorstore/", include(vectorstore_urls, namespace=vectorstore_namespace)),
    # -----------------------------------
    # Chatbots.
    # mcdaniel: 2026-01-31: are these even reachable anymore?
    # -----------------------------------
    path("chat/", DefaultChatbotApiView.as_view(), name=f"{name_prefix}_chat"),
    path("config/", ChatConfigView.as_view(), name=f"{name_prefix}_config"),
    # -----------------------------------
    # password management
    # -----------------------------------
    path(
        "password-reset-request/",
        PasswordResetRequestView.as_view(),
        name=AccountNamedUrls.ACCOUNT_PASSWORD_RESET_REQUEST,
    ),
    path("password-confirm/", PasswordConfirmView.as_view(), name=AccountNamedUrls.ACCOUNT_PASSWORD_CONFIRM),
    path(
        "password-reset-link/<uidb64>/<token>/", PasswordResetView.as_view(), name=AccountNamedUrls.PASSWORD_RESET_LINK
    ),
    # -----------------------------------
    # static routes
    # -----------------------------------
    path("favicon.png", FaviconView.as_view(), name=f"{name_prefix}_favicon"),
    path("robots.txt", RobotsTxtView.as_view(), name=f"{name_prefix}_robots_txt"),
    path("sitemap.xml", SitemapXmlView.as_view(), name=f"{name_prefix}_sitemap_xml"),
    path("healthz/", HealthzView.as_view(), name=f"{name_prefix}_healthz"),
    path("readiness/", ReadinessView.as_view(), name=f"{name_prefix}_readiness"),
    re_path(
        r"^apple-touch-icon\.png$",
        serve,
        {
            "path": "images/logo/apple-touch-icon.png",
            "document_root": settings.STATIC_ROOT,
        },
    ),
    re_path(
        r"^apple-touch-icon-precomposed\.png$",
        serve,
        {
            "path": "images/logo/apple-touch-icon.png",
            "document_root": settings.STATIC_ROOT,
        },
    ),
    # -----------------------------------
    # routes for 3rd party apps
    # -----------------------------------
    path("social-auth/", include(social_django_urls, namespace="social_auth")),
]


# mcdaniel 2026-01-20: converting static() to list(static(...)) to fix
# Sphinx doc build error: 'TypeError: can only concatenate list (not "static") to list
#
urlpatterns += list(static(settings.STATIC_URL, document_root=settings.STATIC_ROOT))

if smarter_settings.environment == SmarterEnvironments.LOCAL and smarter_settings.debug_mode and not "test" in sys.argv:
    # we need to limit this to local because the debug toolbar is only installed on the local build
    # debug_model == True does not not guarantee that the debug toolbar is actually installed
    try:
        import debug_toolbar

        urlpatterns += [
            path("__debug__/", include(debug_toolbar.urls)),
        ]
        logger.debug(
            "%s Debug mode is enabled, and debug_toolbar is installed. Added debug_toolbar URLs to urlpatterns.",
            formatted_text(__name__),
        )
    except ImportError:
        logger.warning(
            "%s Debug mode is enabled, but debug_toolbar is not installed. Install debug_toolbar to use the Django Debug Toolbar.",
            formatted_text(__name__),
        )


__all__ = ["urlpatterns"]
