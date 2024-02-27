# -*- coding: utf-8 -*-
"""URL configuration for the web platform."""

from django.urls import include, path

from .views.account import (
    account,
    account_limits,
    account_organization,
    account_profile,
    account_team,
)
from .views.authentication import LogoutView, login_redirector
from .views.dashboard import (
    api_keys,
    dashboard,
    documentation,
    notifications,
    platform_help,
    plugins,
    usage,
)
from .views.profile import language, profile, sign_out


urlpatterns = [
    path("", dashboard, name="home"),
    path("login/", login_redirector, name="login_redirector"),
    path("api-auth/logout/", LogoutView.as_view(), name="logout"),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("api-keys/", api_keys, name="api_keys"),
    path("plugins/", plugins, name="plugins"),
    path("usage/", usage, name="usage"),
    path("notifications/", notifications, name="notifications"),
    path("account/", account, name="account"),
    path("account/limits/", account_limits, name="account_limits"),
    path("account/organization/", account_organization, name="account_organization"),
    path("account/profile/", account_profile, name="account_profile"),
    path("account/team/", account_team, name="account_team"),
    path("documentation/", documentation, name="documentation"),
    path("help/", platform_help, name="help"),
    path("profile/", profile, name="profile"),
    path("language/", language, name="language"),
    path("sign-out/", sign_out, name="sign_out"),
]
