# -*- coding: utf-8 -*-
"""URL configuration for the web platform."""

from django.urls import include, path

from smarter.apps.account.views.account import (  # AccountAPIKeysView,; AccountLimitsView,; AccountOrganizationView,; AccountProfileView,; AccountTeamView,; AccountUsageView,
    AccountView,
)
from smarter.apps.account.views.authentication import (
    AccountDeactivateView,
    ConfirmPasswordView,
    LoginView,
    LogoutView,
    NewPasswordView,
    ResetPasswordView,
    SignUpView,
    VerifyEmailView,
    WelcomeView,
)


urlpatterns = [
    path("", AccountView.as_view(), name="account"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/", SignUpView.as_view(), name="register"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
    path("new-password/", NewPasswordView.as_view(), name="new-password"),
    path("confirm-password/", ConfirmPasswordView.as_view(), name="confirm-password"),
    path("welcome/", WelcomeView.as_view(), name="welcome"),
    path("deactivate/", AccountDeactivateView.as_view(), name="deactivate"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("dashboard/", include("smarter.apps.account.urls_dashboard")),
]
