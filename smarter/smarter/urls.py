"""URL configuration for Smarter Api and web console."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path, re_path
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls
from wagtail_transfer import urls as wagtailtransfer_urls

from smarter.apps.account.views.authentication import (
    AccountRegisterView,
    LoginView,
    LogoutView,
)
from smarter.apps.chatapp.views import ChatConfigView
from smarter.apps.chatbot.api.v1.views.default import DefaultChatBotApiView
from smarter.apps.chatbot.models import get_cached_chatbot_by_request
from smarter.apps.dashboard.admin import restricted_site
from smarter.apps.dashboard.views.dashboard import ComingSoon
from smarter.apps.docs.views.webserver import (
    FaviconView,
    HealthzView,
    ReadinessView,
    RobotsTxtView,
    SitemapXmlView,
)


admin.site = restricted_site

# Load the admin modules of all installed apps
# and register their models with the custom admin site
admin.autodiscover()


def root_redirector(request):
    """
    Handles traffic sent to the root of the website. Requests
    can take the form of:
    1. a chatbot endpoint if the user is not authenticated and the
       url is of any of the following forms
       - https://example.3141-5926-5359.api.smarter.sh/
       - https://example.3141-5926-5359.api.smarter.sh/config/
       - localhost:8000/api/v1/chatbots/1/chat/
       - localhost:8000/api/v1/chatbots/1/chat/config/
       - localhost:8000/api/v1/cli/chat/example/
       - localhost:8000/api/v1/cli/chat/example/config/
    2. the dashboard if the user is authenticated,
    3. otherwise to the Wagtail docs homepage.
    """
    # 1. check if the url is a chatbot endpoint
    chatbot = get_cached_chatbot_by_request(request=request)
    if chatbot:
        view = DefaultChatBotApiView.as_view()
        return view(request, chatbot_id=chatbot.id)

    # 2. check if the user is authenticated, if so redirect to the dashboard
    if request.user.is_authenticated:
        return redirect("/dashboard/")

    # 3. otherwise redirect to the Wagtail docs homepage
    return redirect("/docs/")


def config_redirector(request):
    """
    Handles traffic sent to the config endpoints of the website.
    """
    chatbot = get_cached_chatbot_by_request(request=request)
    if chatbot:
        view = ChatConfigView.as_view()
        return view(request, chatbot_id=chatbot.id)


urlpatterns = [
    path("", root_redirector, name="home"),
    path("config/", config_redirector, name="root_config"),
    # production smarter platform
    # -----------------------------------
    path("favicon.ico", FaviconView.as_view(), name="favicon"),
    path("robots.txt", RobotsTxtView.as_view(), name="robots_txt"),
    path("sitemap.xml", SitemapXmlView.as_view(), name="sitemap_xml"),
    path("healthz/", HealthzView.as_view(), name="healthz"),
    path("readiness/", ReadinessView.as_view(), name="readiness"),
    # -----------------------------------
    path("account/", include("smarter.apps.account.urls", namespace="account")),
    path("api/", include("smarter.apps.api.urls")),
    path("chatbots/", include("smarter.apps.chatapp.urls")),
    path("dashboard/", include("smarter.apps.dashboard.urls")),
    # django admin
    # -----------------------------------
    path("admin/docs/", include("django.contrib.admindocs.urls")),
    path("admin/", admin.site.urls, name="django_admin"),
    #
    # Wagtail root
    # -----------------------------------
    path("docs/", include("smarter.apps.docs.urls", namespace="docs")),
    # -----------------------------------
    #
    # shortcuts for authentication views
    # -----------------------------------
    path("login/", LoginView.as_view(), name="login_view"),
    path("logout/", LogoutView.as_view(), name="logout_view"),
    path("register/", AccountRegisterView.as_view(), name="register_view"),
    path("social-auth/", include("social_django.urls", namespace="social")),
    # -----------------------------------
    # stripe urls
    # see: https://dj-stripe.dev/dj-stripe/
    # -----------------------------------
    # path("stripe/", include("djstripe.urls", namespace="djstripe")),
    # -----------------------------------
    # Smarter waitlist signup
    # -----------------------------------
    path("waitlist/", ComingSoon.as_view(), name="waitlist"),
    # -----------------------------------
    # wagtail urls
    # -----------------------------------
    path("documents/", include(wagtaildocs_urls)),
    path("cms/", include("smarter.apps.cms.urls")),
    re_path(r"^wagtail-transfer/", include(wagtailtransfer_urls)),
    re_path(r"", include(wagtail_urls)),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# if settings.DEBUG:
#     import debug_toolbar

# urlpatterns += [
#     path("__debug__/", include(debug_toolbar.urls)),
# ]
