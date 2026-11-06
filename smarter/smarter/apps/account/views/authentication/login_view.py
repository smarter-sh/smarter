"""Django Account Authentication Login view."""

import traceback
from typing import Optional, Union

from django import forms
from django.contrib.auth import authenticate, login
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.translation import gettext as _

from smarter.apps.account.login_audit import (
    LoginFailure,
    log_login_failure,
    login_identity,
    password_failure,
)
from smarter.apps.account.models import User, get_resolved_user
from smarter.apps.account.oauth import github_oauth_enabled, google_oauth_enabled
from smarter.lib import logging
from smarter.lib.django import waffle
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseBadRequest,
    SmarterHttpResponseServerError,
)
from smarter.lib.django.views import (
    SmarterNeverCachedWebView,
    redirect_and_expire_cache,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING, SmarterWaffleSwitches.VIEW_LOGGING]
)


class LoginView(SmarterNeverCachedWebView):
    """View for logging in browser session."""

    class LoginForm(forms.Form):
        """Form for the sign-in page."""

        email = forms.EmailField()
        password = forms.CharField(widget=forms.PasswordInput)

    template_path = "account/authentication/sign-in.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logger.debug(
            "%s.__init__() called with args: %s, kwargs: %s. is_google_oauth_enabled: %s, is_github_oauth_enabled: %s",
            self.formatted_class_name,
            args,
            kwargs,
            self.is_google_oauth_enabled,
            self.is_github_oauth_enabled,
        )

    @property
    def formatted_class_name(self):
        """The class name, formatted for log messages."""
        return f"{logging.SmarterFormattedText.text(__name__)}.{LoginView.__name__}"

    @property
    def is_google_oauth_enabled(self) -> bool:
        """
        Whether the sign-in page shows the Google button.

        See :func:`smarter.apps.account.oauth.google_oauth_enabled`.

        :return: True if Google OAuth is enabled, False otherwise.
        :rtype: bool
        """
        return google_oauth_enabled()

    @property
    def is_github_oauth_enabled(self) -> bool:
        """
        Whether the sign-in page shows the GitHub button.

        See :func:`smarter.apps.account.oauth.github_oauth_enabled`.

        :return: True if GitHub OAuth is enabled, False otherwise.
        :rtype: bool
        """
        return github_oauth_enabled()

    def get(self, request, *args, **kwargs) -> Union[HttpResponseRedirect, HttpResponse]:
        """
        Render the login form, or redirect a signed-in user to ``/``.

        The form shows the Google and GitHub buttons, sign-up and footer links per their settings and switches.

        :param request: The request.
        :returns: The rendered form, or the redirect.
        """
        logger.debug(
            "%s.LoginView.get() called with request type: %s %s", self.formatted_class_name, type(request), request
        )
        user = (
            get_resolved_user(request.user)
            if request and hasattr(request, "user") and request.user is not None
            else None
        )
        if user and hasattr(user, "is_authenticated") and user.is_authenticated:
            return redirect_and_expire_cache(path="/")
        form = LoginView.LoginForm()
        context = {
            "form": form,
            "is_google_oauth_enabled": self.is_google_oauth_enabled,
            "is_github_oauth_enabled": self.is_github_oauth_enabled,
            "is_signup_enabled": waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_ACCOUNT_REGISTRATION),
            "are_login_footer_links_enabled": waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_LOGIN_FOOTER_LINKS),
        }
        return self.clean_http_response(request, template_path=self.template_path, context=context)

    def invalid_credentials_response(self, request) -> SmarterHttpResponseBadRequest:
        """
        Answer a failed sign-in, whether the email is unknown or the password is wrong.

        Both cases get the same status and message, so that the response doesn't reveal
        which email addresses have accounts.

        :param request: The request.
        :returns: A ``400`` response.
        """
        return SmarterHttpResponseBadRequest(request=request, error_message=_("Email and/or password do not match."))

    def post(self, request, *args, **kwargs) -> Union[
        HttpResponseRedirect,
        SmarterHttpResponseBadRequest,
        SmarterHttpResponseServerError,
    ]:
        """Handle POST request to log in user with email and password."""
        logger.debug(
            "%s.LoginView.post() called with request type: %s %s, args: %s, kwargs: %s",
            self.formatted_class_name,
            type(request),
            request,
            args,
            kwargs,
        )
        form = LoginView.LoginForm(request.POST)
        authenticated_user: Optional[User] = None
        if form.is_valid():
            email = form.cleaned_data["email"]
            try:
                user = User.objects.get(email=form.cleaned_data["email"])
                password = form.cleaned_data["password"]
                authenticated_user = authenticate(request, username=user.username, password=password)  # type: ignore[assignment]
                if authenticated_user is not None:
                    login(request, authenticated_user)
                    logger.debug(
                        "%s.LoginView.post() authentication succeeded for identity %s",
                        self.formatted_class_name,
                        login_identity(email),
                    )
                    return redirect_and_expire_cache(path="/")
                log_login_failure(email, password_failure(user))
                return self.invalid_credentials_response(request)
            except User.DoesNotExist:
                # the same response as a wrong password, so that sign-in doesn't reveal which emails have accounts.
                log_login_failure(email, LoginFailure.UNKNOWN_ACCOUNT)
                return self.invalid_credentials_response(request)
            # pylint: disable=W0718
            except Exception as e:
                log_login_failure(email, LoginFailure.ERROR)
                logger.error(
                    "%s.LoginView.post() sign-in of identity %s raised an exception: %s\n%s",
                    self.formatted_class_name,
                    login_identity(email),
                    e,
                    traceback.format_exc(),
                )
                # the exception's text is logged above, and never shown to the client.
                return SmarterHttpResponseServerError(
                    request=request, error_message=_("An unknown error occurred. Please try again later.")
                )
        log_login_failure(request.POST.get("email"), LoginFailure.INVALID_FORM)
        logger.debug(
            "%s.LoginView.post() invalid form data received in fields: %s",
            self.formatted_class_name,
            list(form.errors.keys()),
        )
        return SmarterHttpResponseBadRequest(request=request, error_message=_("Received invalid responses."))
