"""URL configuration for Smarter Api and web console."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from smarter.apps.account.views.authentication import (
    AccountRegisterView,
    LoginView,
    LogoutView,
)
from smarter.apps.dashboard.admin import restricted_site


admin.site = restricted_site

# This will load the admin modules of all installed apps
# and register their models with your custom admin site
admin.autodiscover()


urlpatterns = [
    path("chatapp/", include("smarter.apps.chatapp.urls")),
    path("", include("smarter.apps.dashboard.urls")),
    path("admin/", admin.site.urls),
    path("api/", include("smarter.apps.api.urls")),
    # shortcuts for authentication views
    # -----------------------------------
    path("login/", LoginView.as_view(), name="login_view"),
    path("logout/", LogoutView.as_view(), name="logout_view"),
    path("register/", AccountRegisterView.as_view(), name="register_view"),
    # -----------------------------------
    # -----------------------------------
    # see: https://dj-stripe.dev/dj-stripe/
    path("stripe/", include("djstripe.urls", namespace="djstripe")),
    # -----------------------------------
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
