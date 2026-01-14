# pylint: disable=W0613
"""Django Authentication views."""
import logging
import traceback
from typing import Optional, Union

from django import forms
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse

from smarter.apps.account.models import User, get_resolved_user
from smarter.common.conf import smarter_settings
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.helpers.email_helpers import email_helper
from smarter.lib.django import waffle
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseBadRequest,
    SmarterHttpResponseForbidden,
    SmarterHttpResponseNotFound,
    SmarterHttpResponseServerError,
)
from smarter.lib.django.token_generators import (
    ExpiringTokenGenerator,
    SmarterTokenConversionError,
    SmarterTokenExpiredError,
    SmarterTokenIntegrityError,
    SmarterTokenParseError,
)
from smarter.lib.django.view_helpers import (
    SmarterAuthenticatedNeverCachedWebView,
    SmarterNeverCachedWebView,
    redirect_and_expire_cache,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.ACCOUNT_LOGGING) and waffle.switch_is_active(
        SmarterWaffleSwitches.VIEW_LOGGING
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
class LoginView(SmarterNeverCachedWebView):
    """View for logging in browser session."""

    class LoginForm(forms.Form):
        """Form for the sign-in page."""

        email = forms.EmailField()
        password = forms.CharField(widget=forms.PasswordInput)

    template_path = "account/authentication/sign-in.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.formatted_class_name = formatted_text(f"{__name__}.{self.__class__.__name__}")
        logger.debug(
            "%s.__init__() called with args: %s, kwargs: %s. is_google_oauth_enabled: %s, is_github_oauth_enabled: %s",
            self.formatted_class_name,
            args,
            kwargs,
            self.is_google_oauth_enabled,
            self.is_github_oauth_enabled,
        )

    @property
    def is_google_oauth_enabled(self) -> bool:
        """
        Check if Google OAuth is enabled. If True, the sign-in page
        will show the Google OAuth sign-in option. To return True,
        both the key and secret must be set in settings, and
        the appropriate authentication backend must be included
        in Django settings.AUTHENTICATION_BACKENDS.

        See: https://docs.djangoproject.com/en/6.0/topics/auth/customizing/

        :return: True if Google OAuth is enabled, False otherwise.
        :rtype: bool
        """
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
            "smarter.lib.django.auth.GoogleOAuth2",
            "smarter.lib.django.auth.GoogleOAuth2Multitenant",
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
        Check if GitHub OAuth is enabled. If True, the sign-in page
        will show the GitHub OAuth sign-in option. To return True,
        both the key and secret must be set in settings, and
        the appropriate authentication backend must be included
        in Django settings.AUTHENTICATION_BACKENDS.

        See: https://docs.djangoproject.com/en/6.0/topics/auth/customizing/

        :return: True if GitHub OAuth is enabled, False otherwise.
        :rtype: bool
        """
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
            "smarter.lib.django.auth.GithubOAuth2",
            "smarter.lib.django.auth.GithubOAuth2Multitenant",
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
        logger.info(
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
        }
        return self.clean_http_response(request, template_path=self.template_path, context=context)

    def post(self, request, *args, **kwargs) -> Union[
        HttpResponseRedirect,
        SmarterHttpResponseBadRequest,
        SmarterHttpResponseForbidden,
        SmarterHttpResponseServerError,
    ]:
        """
        Handle POST request to log in user with email and password.
        """
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


class LogoutView(SmarterNeverCachedWebView):
    """View for logging out browser session."""

    def get(self, request, *args, **kwargs) -> HttpResponseRedirect:
        logout(request)
        return redirect_and_expire_cache(path="/")

    def post(self, request, *args, **kwargs) -> HttpResponseRedirect:
        logout(request)
        return redirect_and_expire_cache(path="/")


class AccountInactiveView(SmarterNeverCachedWebView):
    """View for inactive account page."""

    template_path = "account/authentication/account-inactive.html"

    def get(self, request, *args, **kwargs) -> HttpResponse:
        return self.clean_http_response(request, template_path=self.template_path)


class AccountRegisterView(SmarterNeverCachedWebView):
    """View for signing up."""

    class SignUpForm(forms.Form):
        """Form for the sign-in page."""

        email = forms.EmailField()
        password = forms.CharField(widget=forms.PasswordInput)

    template_path = "account/authentication/sign-up.html"

    def get(self, request, *args, **kwargs) -> Union[HttpResponseRedirect, HttpResponse]:
        user = get_resolved_user(request.user)
        if user and hasattr(user, "is_authenticated") and user.is_authenticated:
            return redirect_and_expire_cache(path="/")

        form = AccountRegisterView.SignUpForm()
        context = {"form": form}
        return self.clean_http_response(request, template_path=self.template_path, context=context)

    def post(self, request, *args, **kwargs) -> Union[HttpResponseRedirect, HttpResponse]:
        form = AccountRegisterView.SignUpForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["email"]
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            User.objects.create_user(username, password=password, email=email)
            authenticated_user = authenticate(request, username=username, password=password)
            if authenticated_user is not None:
                login(request, authenticated_user)
                return redirect_and_expire_cache(path="/welcome/")
            else:
                # pylint: disable=W0719
                raise Exception(
                    f"{self.formatted_class_name}.post() Authentication failed immediately after registration. This is a bug."
                )
        return self.get(request=request)


class AccountActivationEmailView(SmarterAuthenticatedNeverCachedWebView):
    """View for activating an account via an email with a single-use activation link."""

    template_path = "account/activation.html"
    email_template_path = "account/authentication/email/account-activation.html"
    expiring_token = ExpiringTokenGenerator()

    def get(self, request, *args, **kwargs) -> HttpResponse:

        logger.debug(
            "%s.AccountActivationEmailView.get() called with request type: %s %s, args: %s, kwargs: %s",
            self.formatted_class_name,
            type(request),
            request,
            args,
            kwargs,
        )

        # generate and send the activation email
        user = get_resolved_user(request.user)
        if not isinstance(user, User) or not hasattr(user, "is_authenticated") or not user.is_authenticated:
            logger.debug(
                "%s.AccountActivationEmailView.get() user is not authenticated or not found: %s",
                self.formatted_class_name,
                user,
            )
            return SmarterHttpResponseNotFound(
                request=request, error_message="User not found. Please log in to activate your account."
            )
        # pylint: disable=C0415
        from smarter.apps.account.urls import AccountNamedUrls

        url = self.expiring_token.encode_link(
            request, user, AccountNamedUrls.namespace + ":" + AccountNamedUrls.ACCOUNT_ACTIVATE
        )
        context = {
            "account_activation": {
                "url": url,
            }
        }
        body = self.render_clean_html(request, template_path=self.email_template_path, context=context)
        subject = "Activate your account."
        to = user.email
        email_helper.send_email(subject=subject, body=body, to=to, html=True)

        # render a page to let the user know the email was sent. Add a link to resend the email.
        email_resend_url = reverse(AccountNamedUrls.namespace + ":" + AccountNamedUrls.ACCOUNT_ACTIVATION)
        context = {"account_activation": {"resend": email_resend_url}}
        return self.clean_http_response(request, template_path=self.template_path, context=context)


class AccountActivateView(SmarterNeverCachedWebView):
    """View for welcoming a newly activated user to the platform."""

    template_path = "account/welcome.html"
    expiring_token = ExpiringTokenGenerator()

    def get(self, request, *args, **kwargs):
        uidb64 = kwargs.get("uidb64", None)
        token = kwargs.get("token", None)

        try:
            user = self.expiring_token.decode_link(uidb64, token)
            user.is_active = True
            user.save()
        except User.DoesNotExist:
            return SmarterHttpResponseNotFound(
                request=request, error_message="Invalid password reset link. User does not exist."
            )
        except (
            TypeError,
            ValueError,
            OverflowError,
            SmarterTokenParseError,
            SmarterTokenConversionError,
            SmarterTokenIntegrityError,
        ) as e:
            return SmarterHttpResponseBadRequest(request=request, error_message=str(e))
        except SmarterTokenExpiredError as e:
            return SmarterHttpResponseForbidden(request=request, error_message=str(e))

        return self.clean_http_response(request, template_path=self.template_path)


# ------------------------------------------------------------------------------
# Private Access Views
# ------------------------------------------------------------------------------
class AccountDeactivateView(SmarterAuthenticatedNeverCachedWebView):
    """View for the account deactivation page."""

    template_path = "account/account-deactivated.html"
