"""URL configuration for Smarter Api and web console."""

from logging import getLogger

from django.apps import apps
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.admin.exceptions import AlreadyRegistered, NotRegistered
from django.urls import include, path, re_path
from django.views.generic.base import RedirectView
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls
from wagtail_transfer import urls as wagtailtransfer_urls

from smarter.apps.account.const import namespace as account_namespace
from smarter.apps.account.views.authentication import (
    AccountRegisterView,
    LoginView,
    LogoutView,
)
from smarter.apps.api.const import namespace as api_namespace
from smarter.apps.chatbot.api.v1.views.default import DefaultChatbotApiView
from smarter.apps.dashboard.admin import (
    SuperUserOnlyModelAdmin,
    smarter_restricted_admin_site,
)
from smarter.apps.dashboard.const import namespace as dashboard_namespace
from smarter.apps.dashboard.views.dashboard import ComingSoon
from smarter.apps.docs.const import namespace as docs_namespace
from smarter.apps.docs.views.webserver import (
    FaviconView,
    HealthzView,
    ReadinessView,
    RobotsTxtView,
    SitemapXmlView,
)
from smarter.apps.plugin.const import namespace as plugin_namespace
from smarter.apps.prompt.const import namespace as prompt_workbench_namespace
from smarter.apps.prompt.views import ChatConfigView
from smarter.apps.provider.const import namespace as provider_namespace


logger = getLogger(__name__)

# -----------------------------------------------------------------------------
# Initialize custom admin site for Smarter
# -----------------------------------------------------------------------------
admin.site = smarter_restricted_admin_site
admin.autodiscover()

models = apps.get_models()
for model in models:
    try:
        # Register all non-Smarter models with the SuperUserOnlyModelAdmin
        # to restrict access to superusers only
        smarter_restricted_admin_site.register(model, SuperUserOnlyModelAdmin)
    except AlreadyRegistered:
        pass
try:
    # Unregister the Knox AuthToken model since we subclassed this
    # and created our own admin for it.
    from knox.models import AuthToken

    smarter_restricted_admin_site.unregister(AuthToken)
except NotRegistered as e:
    logger.warning("Could not unregister AuthToken model because it is not registered: %s", e)

name_prefix = "root"


urlpatterns = [
    path("", RedirectView.as_view(pattern_name="dashboard:dashboard"), name=f"{name_prefix}_home"),
    # -----------------------------------
    # root paths
    # -----------------------------------
    path("account/", include("smarter.apps.account.urls", namespace=account_namespace)),
    path("admin/", admin.site.urls, name="django_admin"),
    path("admin/docs/", include("django.contrib.admindocs.urls")),
    path("api/", include("smarter.apps.api.urls", namespace=api_namespace)),
    path("chat/", DefaultChatbotApiView.as_view(), name=f"{name_prefix}_chat"),
    path("cms/", include("smarter.apps.cms.urls", namespace=None)),
    path("config/", ChatConfigView.as_view(), name=f"{name_prefix}_config"),
    path("dashboard/", include("smarter.apps.dashboard.urls", namespace=dashboard_namespace)),
    path("workbench/", include("smarter.apps.prompt.urls", namespace=prompt_workbench_namespace)),
    path("docs/", include("smarter.apps.docs.urls", namespace=docs_namespace)),
    path("login/", LoginView.as_view(), name="login_view"),
    path("logout/", LogoutView.as_view(), name="logout_view"),
    path("plugin/", include("smarter.apps.plugin.urls", namespace=plugin_namespace)),
    path("provider/", include("smarter.apps.provider.urls", namespace=provider_namespace)),
    path("register/", AccountRegisterView.as_view(), name=f"{name_prefix}_register_view"),
    # -----------------------------------
    # static routes
    # -----------------------------------
    path("favicon.ico", FaviconView.as_view(), name=f"{name_prefix}_favicon"),
    path("robots.txt", RobotsTxtView.as_view(), name=f"{name_prefix}_robots_txt"),
    path("sitemap.xml", SitemapXmlView.as_view(), name=f"{name_prefix}_sitemap_xml"),
    path("healthz/", HealthzView.as_view(), name=f"{name_prefix}_healthz"),
    path("readiness/", ReadinessView.as_view(), name=f"{name_prefix}_readiness"),
    path("waitlist/", ComingSoon.as_view(), name=f"{name_prefix}_waitlist"),
    # -----------------------------------
    # routes for 3rd party apps
    # -----------------------------------
    path("social-auth/", include("social_django.urls", namespace="social_auth")),
    # -----------------------------------
    # stripe urls
    # see: https://dj-stripe.dev/dj-stripe/
    # -----------------------------------
    # path("stripe/", include("djstripe.urls", namespace="djstripe")),
    # -----------------------------------
    # -----------------------------------
    # IMPORTANT: place these wagtail routes at the end of the urlpatterns
    # -----------------------------------
    path("documents/", include(wagtaildocs_urls)),
    re_path(r"^wagtail-transfer/", include(wagtailtransfer_urls)),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if not settings.DEBUG:
    # only serve media files when not running locally in debug mode
    urlpatterns += [re_path(r"", include(wagtail_urls))]

# if settings.DEBUG:
#     import debug_toolbar
# urlpatterns += [
#     path("__debug__/", include(debug_toolbar.urls)),
# ]
