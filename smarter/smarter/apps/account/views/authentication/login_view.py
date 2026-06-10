"""Django Account Authentication Login view."""

import traceback
from typing import Optional, Union

from django import forms
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.http import HttpResponse, HttpResponseRedirect

from smarter.apps.account.models import User, get_resolved_user
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django import waffle
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseBadRequest,
    SmarterHttpResponseForbidden,
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
        return self.formatted_text(f"{__name__}.{LoginView.__name__}")

    @property
    def is_google_oauth_enabled(self) -> bool:
        """
        Check if Google OAuth is enabled.

        If True, the sign-in page
        will show the Google OAuth sign-in option. To return True,
        both the key and secret must be set in settings, and
        the appropriate authentication backend must be included
        in Django settings.AUTHENTICATION_BACKENDS.

        See: https://docs.djangoproject.com/en/6.0/topics/auth/customizing/

        :return: True if Google OAuth is enabled, False otherwise.
        :rtype: bool
        """
        if not waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_OAUTH2):
            logger.debug(
                "%s.is_google_oauth_enabled() waffle switch %s is not active. Returning False",
                self.formatted_class_name,
                SmarterWaffleSwitches.ENABLE_OAUTH2,
            )
            return False
        if smarter_settings.social_auth_google_oauth2_key.get_secret_value() in (
            "",
            None,
            smarter_settings.default_missing_value,
        ):
            logger.debug(
                "%s.is_google_oauth_enabled() smarter_settings.social_auth_google_oauth2_key Google OAuth2 key is not set. Returning False",
                self.formatted_class_name,
            )
            return False
        if smarter_settings.social_auth_google_oauth2_secret.get_secret_value() in (
            "",
            None,
            smarter_settings.default_missing_value,
        ):
            logger.debug(
                "%s.is_google_oauth_enabled() smarter_settings.social_auth_google_oauth2_secret Google OAuth2 secret is not set. Returning False",
                self.formatted_class_name,
            )
            return False

        google_oauth_backends = [
            "social_core.backends.google.GoogleOAuth2",
            "smarter.lib.social_core.backends.multitenant.GoogleOAuth2Multitenant",
        ]
        for backend in google_oauth_backends:
            if backend in settings.AUTHENTICATION_BACKENDS:
                return True

        logger.warning(
            "%s.is_google_oauth_enabled() Google oAuth credentials were found in smarter_settings, however, No Google OAuth2 backend found in settings.AUTHENTICATION_BACKENDS. Returning False. Valid Google oauth authentication backends include: %s",
            self.formatted_class_name,
            google_oauth_backends,
        )
        return False

    @property
    def is_github_oauth_enabled(self) -> bool:
        """
        Check if GitHub OAuth is enabled.

        If True, the sign-in page
        will show the GitHub OAuth sign-in option. To return True,
        both the key and secret must be set in settings, and
        the appropriate authentication backend must be included
        in Django settings.AUTHENTICATION_BACKENDS.

        See: https://docs.djangoproject.com/en/6.0/topics/auth/customizing/

        :return: True if GitHub OAuth is enabled, False otherwise.
        :rtype: bool
        """
        if not waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_OAUTH2):
            logger.debug(
                "%s.is_github_oauth_enabled() waffle switch %s is not active. Returning False",
                self.formatted_class_name,
                SmarterWaffleSwitches.ENABLE_OAUTH2,
            )
            return False
        if smarter_settings.social_auth_github_key.get_secret_value() in (
            "",
            None,
            smarter_settings.default_missing_value,
        ):
            logger.debug(
                "%s.is_github_oauth_enabled() smarter_settings.social_auth_github_key GitHub OAuth key is not set. Returning False",
                self.formatted_class_name,
            )
            return False
        if smarter_settings.social_auth_github_secret.get_secret_value() in (
            "",
            None,
            smarter_settings.default_missing_value,
        ):
            logger.debug(
                "%s.is_github_oauth_enabled() smarter_settings.social_auth_github_secret GitHub OAuth secret is not set. Returning False",
                self.formatted_class_name,
            )
            return False
        github_oauth_backends = [
            "social_core.backends.github.GithubOAuth2",
            "smarter.lib.social_core.backends.multitenant.GithubOAuth2Multitenant",
        ]
        for backend in github_oauth_backends:
            if backend in settings.AUTHENTICATION_BACKENDS:
                return True
        logger.warning(
            "%s.is_github_oauth_enabled() GitHub oAuth credentials were found in smarter_settings, however, No GitHub OAuth2 backend found in settings.AUTHENTICATION_BACKENDS. Returning False. Valid GitHub oauth authentication backends include: %s",
            self.formatted_class_name,
            github_oauth_backends,
        )
        return False

    def get(self, request, *args, **kwargs) -> Union[HttpResponseRedirect, HttpResponse]:
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

    def post(self, request, *args, **kwargs) -> Union[
        HttpResponseRedirect,
        SmarterHttpResponseBadRequest,
        SmarterHttpResponseForbidden,
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
                        "%s.LoginView.post() authentication succeeded for user %s", self.formatted_class_name, email
                    )
                    return redirect_and_expire_cache(path="/")
                logger.debug("%s.LoginView.post() authentication failed for user %s", self.formatted_class_name, email)
                return SmarterHttpResponseBadRequest(
                    request=request, error_message="Username and/or password do not match."
                )
            except User.DoesNotExist:
                logger.debug("%s.LoginView.post() no user found with email %s", self.formatted_class_name, email)
                return SmarterHttpResponseForbidden(
                    request=request, error_message=f"Invalid login attempt. Unknown user {email}"
                )
            # pylint: disable=W0718
            except Exception as e:
                logger.debug(
                    "%s.LoginView.post() encountered an unknown error for user %s: %s\n%s",
                    self.formatted_class_name,
                    email,
                    e,
                    traceback.format_exc(),
                )
                return SmarterHttpResponseServerError(request=request, error_message=f"An unknown error occurred {e}")
        logger.debug("%s.LoginView.post() invalid form data received: %s", self.formatted_class_name, form.errors)
        return SmarterHttpResponseBadRequest(request=request, error_message="Received invalid responses.")
