# -*- coding: utf-8 -*-
"""URL configuration for smarter project."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from smarter.apps.account.views.authentication import (
    LoginView,
    LogoutView,
    SignUpView,
    WelcomeView,
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
    path("register/", SignUpView.as_view(), name="register_view"),
    path("welcome/", WelcomeView.as_view(), name="welcome_view"),
    # -----------------------------------
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
