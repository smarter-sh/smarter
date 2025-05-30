"""URL configuration for Smarter Api and web console."""

from logging import getLogger

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.core.handlers.wsgi import WSGIRequest
from django.shortcuts import redirect
from django.urls import include, path, re_path, reverse
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
from smarter.apps.chatbot.models import get_cached_chatbot_by_request
from smarter.apps.dashboard.admin import restricted_site
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


logger = getLogger(__name__)

admin.site = restricted_site

# Load the admin modules of all installed apps
# and register their models with the custom admin site
admin.autodiscover()

name_prefix = "root"


def root_redirector(request: WSGIRequest) -> RedirectView:
    """
    Handles traffic sent to the root of the website. Requests
    can take the form of:
    1. a chatbot endpoint if the user is not authenticated and the
       url is of any of the following forms
       - https://example.3141-5926-5359.api.smarter.sh/
       - https://example.3141-5926-5359.api.smarter.sh/config/
       - localhost:8000/api/v1/workbench/1/chat/
       - localhost:8000/api/v1/workbench/1/chat/config/
       - localhost:8000/api/v1/cli/chat/example/
       - localhost:8000/api/v1/cli/chat/example/config/
    2. the dashboard if the user is authenticated,
    3. otherwise to the Wagtail docs homepage.
    """
    # 1. check if the url is a chatbot endpoint
    chatbot = get_cached_chatbot_by_request(request=request)
    if chatbot:
        view = DefaultChatbotApiView.as_view()
        return view(request, chatbot_id=chatbot.id)

    # 2. check if the user is authenticated, if so redirect to the dashboard
    if request.user.is_authenticated:
        return redirect(reverse("dashboard:dashboard"))

    # 3. otherwise redirect to the Wagtail docs homepage
    return redirect("/docs/")


def config_redirector(request: WSGIRequest) -> ChatConfigView:
    """
    Handles traffic sent to the config endpoints of the website.
    """
    chatbot = get_cached_chatbot_by_request(request=request)
    if chatbot:
        view = ChatConfigView.as_view()
        return view(request, chatbot_id=chatbot.id)
    return redirect("/docs/")


urlpatterns = [
    # -----------------------------------
    # routes for named urls.
    # https://example.3141-5926-5359.api.smarter.sh/
    # -----------------------------------
    path("", root_redirector, name=f"{name_prefix}_home"),
    path("config/", config_redirector, name=f"{name_prefix}_config"),
    # -----------------------------------
    # static routes
    # -----------------------------------
    path("favicon.ico", FaviconView.as_view(), name=f"{name_prefix}_favicon"),
    path("robots.txt", RobotsTxtView.as_view(), name=f"{name_prefix}_robots_txt"),
    path("sitemap.xml", SitemapXmlView.as_view(), name=f"{name_prefix}_sitemap_xml"),
    path("healthz/", HealthzView.as_view(), name=f"{name_prefix}_healthz"),
    path("readiness/", ReadinessView.as_view(), name=f"{name_prefix}_readiness"),
    path("register/", AccountRegisterView.as_view(), name=f"{name_prefix}_register_view"),
    path("waitlist/", ComingSoon.as_view(), name=f"{name_prefix}_waitlist"),
    # -----------------------------------
    # namespaced routes for apps
    # -----------------------------------
    path("account/", include("smarter.apps.account.urls", namespace=account_namespace)),
    path("admin/", admin.site.urls, name="django_admin"),
    path("admin/docs/", include("django.contrib.admindocs.urls")),
    path("api/", include("smarter.apps.api.urls", namespace=api_namespace)),
    path(
        "chatbots/",
        RedirectView.as_view(url="dashboard/", permanent=True),
    ),
    path("cms/", include("smarter.apps.cms.urls", namespace=None)),
    path("dashboard/", include("smarter.apps.dashboard.urls", namespace=dashboard_namespace)),
    path("docs/", include("smarter.apps.docs.urls", namespace=docs_namespace)),
    path("plugin/", include("smarter.apps.plugin.urls", namespace=plugin_namespace)),
    path("workbench/", include("smarter.apps.prompt.urls", namespace=prompt_workbench_namespace)),
    # -----------------------------------
    # authentication routes
    # -----------------------------------
    path("login/", LoginView.as_view(), name="login_view"),
    path("logout/", LogoutView.as_view(), name="logout_view"),
    path("social-auth/", include("social_django.urls", namespace="social_auth")),
    # -----------------------------------
    # stripe urls
    # see: https://dj-stripe.dev/dj-stripe/
    # -----------------------------------
    # path("stripe/", include("djstripe.urls", namespace="djstripe")),
    # -----------------------------------
    # -----------------------------------
    # wagtail routes (place these at the end of the urlpatterns)
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
