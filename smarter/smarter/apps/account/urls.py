# -*- coding: utf-8 -*-
"""URL configuration for the web platform."""

from django.urls import path

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
    # path("limits/", AccountLimitsView.as_view(), name="account_limits"),
    # path("organization/", AccountOrganizationView.as_view(), name="account_organization"),
    # path("profile/", AccountProfileView.as_view(), name="account_profile"),
    # path("team/", AccountTeamView.as_view(), name="account_team"),
    # path("api-keys/", AccountAPIKeysView.as_view(), name="account_api_keys"),
    # path("usage/", AccountUsageView.as_view(), name="account_usage"),
]
