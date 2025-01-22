"""URL configuration for the web platform."""

from django.urls import include, path
from django.views.generic.base import RedirectView

from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SmarterEnvironments

from .views.authentication import (
    AccountActivateView,
    AccountActivationEmailView,
    AccountDeactivateView,
    AccountRegisterView,
    LoginView,
    LogoutView,
)
from .views.password_management import (
    PasswordConfirmView,
    PasswordResetRequestView,
    PasswordResetView,
)


urlpatterns = [
    path(
        "",
        RedirectView.as_view(url="/dashboard/account/dashboard/", permanent=False),
        name="dashboard_account_dashboard",
    ),
    path("login/", LoginView.as_view(), name="account_login"),
    path("logout/", LogoutView.as_view(), name="account_logout"),
    path("dashboard/", include("smarter.apps.account.views.dashboard.urls")),
    # account lifecycle
    path("register/", AccountRegisterView.as_view(), name="account_register"),
    path("activation/", AccountActivationEmailView.as_view(), name="account_activation"),
    path("activate/<uidb64>/<token>/", AccountActivateView.as_view(), name="account_activate"),
    path("deactivate/", AccountDeactivateView.as_view(), name="account_deactivate"),
    # password management
    path("password-reset-request/", PasswordResetRequestView.as_view(), name="account_password_reset_request"),
    path("password-confirm/", PasswordConfirmView.as_view(), name="account_password_confirm"),
    path("password-reset-link/<uidb64>/<token>/", PasswordResetView.as_view(), name="password_reset_link"),
]

if smarter_settings.environment == SmarterEnvironments.LOCAL:
    from .views.email import EmailWelcomeView

    urlpatterns.append(path("email/welcome/<first_name>/", EmailWelcomeView.as_view(), name="welcome"))
