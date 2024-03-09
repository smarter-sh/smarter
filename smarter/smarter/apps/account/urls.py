# -*- coding: utf-8 -*-
"""URL configuration for the web platform."""

from django.urls import include, path

from smarter.apps.account.views.account import AccountView
from smarter.apps.account.views.authentication import (
    AccountDeactivateView,
    AccountRegisterView,
    AccountWelcomeView,
    EmailVerifyView,
    LoginView,
    LogoutView,
)
from smarter.apps.account.views.password_management import (
    PasswordConfirmView,
    PasswordResetRequestView,
    PasswordResetView,
)


urlpatterns = [
    path("", AccountView.as_view(), name="account"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("dashboard/", include("smarter.apps.account.urls_dashboard")),
    # account lifecycle
    path("register/", AccountRegisterView.as_view(), name="register"),
    path("welcome/", AccountWelcomeView.as_view(), name="welcome"),
    path("deactivate/", AccountDeactivateView.as_view(), name="deactivate"),
    path("email-verify/", EmailVerifyView.as_view(), name="verify-email"),
    # password management
    path("password-reset-request/", PasswordResetRequestView.as_view(), name="password_reset_request"),
    path("password-confirm/", PasswordConfirmView.as_view(), name="password_confirm"),
    path("password-reset-link/<uidb64>/<token>/", PasswordResetView.as_view(), name="password_reset_link"),
]
