"""URL configuration for Smarter Api and web console."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls
from wagtail_transfer import urls as wagtailtransfer_urls

from smarter.apps.account.views.authentication import (
    AccountRegisterView,
    LoginView,
    LogoutView,
)
from smarter.apps.dashboard.admin import restricted_site
from smarter.apps.dashboard.views.dashboard import ComingSoon


admin.site = restricted_site

# This will load the admin modules of all installed apps
# and register their models with your custom admin site
admin.autodiscover()


urlpatterns = [
    path("", RedirectView.as_view(url="/docs/")),
    # django admin
    # -----------------------------------
    path("admin/docs/", include("django.contrib.admindocs.urls")),
    path("admin/", admin.site.urls, name="django_admin"),
    # smarter platform
    # -----------------------------------
    path("api/", include("smarter.apps.api.urls")),
    path("chatapp/", include("smarter.apps.chatapp.urls")),
    path("dashboard/", include("smarter.apps.dashboard.urls")),
    #
    # documentation pages that are not part of the wagtail site
    # -----------------------------------
    path("docs/", include("smarter.apps.docs.urls")),
    # -----------------------------------
    #
    # shortcuts for authentication views
    # -----------------------------------
    path("login/", LoginView.as_view(), name="login_view"),
    path("logout/", LogoutView.as_view(), name="logout_view"),
    path("register/", AccountRegisterView.as_view(), name="register_view"),
    # -----------------------------------
    # stripe urls
    # see: https://dj-stripe.dev/dj-stripe/
    # -----------------------------------
    path("stripe/", include("djstripe.urls", namespace="djstripe")),
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
