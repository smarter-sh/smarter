"""Django Account Authentication views."""

import traceback
from typing import Union

from django import forms
from django.contrib.auth import authenticate, login
from django.http import HttpResponse, HttpResponseRedirect

from smarter.apps.account.models import User, get_resolved_user
from smarter.common.helpers.email_helpers import email_helper
from smarter.lib import logging
from smarter.lib.django.http.shortcuts import (
    SmarterHttpResponseBadRequest,
    SmarterHttpResponseForbidden,
    SmarterHttpResponseNotFound,
)
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.token_generators import (
    ExpiringTokenGenerator,
    SmarterTokenConversionError,
    SmarterTokenExpiredError,
    SmarterTokenIntegrityError,
    SmarterTokenParseError,
)
from smarter.lib.django.views import (
    SmarterAuthenticatedNeverCachedWebView,
    SmarterNeverCachedWebView,
    redirect_and_expire_cache,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING, SmarterWaffleSwitches.VIEW_LOGGING]
)


# ------------------------------------------------------------------------------
# Public Access Views
# ------------------------------------------------------------------------------
class AccountInactiveView(SmarterNeverCachedWebView):
    """View for inactive account page."""

    template_path = "account/account-inactive.html"

    def get(self, request, *args, **kwargs) -> HttpResponse:
        logger.debug(
            "%s.AccountInactiveView.get() called with request type: %s %s, args: %s, kwargs: %s",
            self.formatted_class_name,
            type(request),
            request,
            args,
            kwargs,
        )
        return self.clean_http_response(request, template_path=self.template_path)


class AccountRegisterView(SmarterNeverCachedWebView):
    """View for signing up."""

    class SignUpForm(forms.Form):
        """Form for the sign-in page."""

        email = forms.EmailField()
        password = forms.CharField(widget=forms.PasswordInput)

    template_path = "account/authentication/sign-up.html"

    def get(self, request, *args, **kwargs) -> Union[HttpResponseRedirect, HttpResponse]:
        logger.debug(
            "%s.AccountRegisterView.get() called with request type: %s %s, args: %s, kwargs: %s",
            self.formatted_class_name,
            type(request),
            request,
            args,
            kwargs,
        )
        user = get_resolved_user(request.user)
        if user and hasattr(user, "is_authenticated") and user.is_authenticated:
            return redirect_and_expire_cache(path="/")

        form = AccountRegisterView.SignUpForm()
        context = {"form": form}
        return self.clean_http_response(request, template_path=self.template_path, context=context)

    def post(self, request, *args, **kwargs) -> Union[HttpResponseRedirect, HttpResponse]:
        logger.debug(
            "%s.AccountRegisterView.post() called with request type: %s %s, args: %s, kwargs: %s",
            self.formatted_class_name,
            type(request),
            request,
            args,
            kwargs,
        )
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
                # pylint: disable=broad-exception-raised
                raise Exception(
                    f"{self.formatted_class_name}.post() Authentication failed immediately after registration. This is a bug."
                )
        return self.get(request=request)


class AccountActivationEmailView(SmarterAuthenticatedNeverCachedWebView):
    """View for activating an account via an email with a single-use activation link."""

    template_path = "account/activation.html"
    email_template_path = "account/authentication/email/account-activation.html"
    expiring_token = ExpiringTokenGenerator()

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{AccountActivationEmailView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

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
            logger.warning(
                "%s.AccountActivationEmailView.get() user is not authenticated or not found: %s",
                self.formatted_class_name,
                user,
            )
            return SmarterHttpResponseNotFound(
                request=request, error_message="User not found. Please log in to activate your account."
            )
        # pylint: disable=C0415
        from smarter.apps.account.urls import AccountReverseNames

        url = self.expiring_token.encode_link(
            request, user, ":".join([AccountReverseNames.namespace, AccountReverseNames.ACCOUNT_ACTIVATE])
        )
        context = {
            "account_activation": {
                "url": url,
            }
        }
        body = self.render_clean_html(request, template_path=self.email_template_path, context=context)
        subject = "Activate your account."
        to = user.email
        logger.debug(
            "%s.AccountActivationEmailView.get() sending account activation email to %s with url: %s",
            self.formatted_class_name,
            to,
            url,
        )
        email_helper.send_email(subject=subject, body=body, to=to, html=True)

        # render a page to let the user know the email was sent. Add a link to resend the email.
        email_resend_url = reverse(AccountReverseNames.namespace, AccountReverseNames.ACCOUNT_ACTIVATION)
        context = {"account_activation": {"resend": email_resend_url}}
        return self.clean_http_response(request, template_path=self.template_path, context=context)


class AccountActivateView(SmarterNeverCachedWebView):
    """View for welcoming a newly activated user to the platform."""

    template_path = "account/welcome.html"
    expiring_token = ExpiringTokenGenerator()

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{AccountActivateView.__name__}[{id(self)}]"
        return logging.formatted_text(class_name)

    def get(self, request, *args, **kwargs):
        logger.debug(
            "%s.AccountActivateView.get() called with request type: %s %s, args: %s, kwargs: %s",
            self.formatted_class_name,
            type(request),
            request,
            args,
            kwargs,
        )
        uidb64 = kwargs.get("uidb64", None)
        token = kwargs.get("token", None)

        try:
            user = self.expiring_token.decode_link(uidb64, token)
            user.is_active = True
            user.save()
        except User.DoesNotExist:
            logger.debug(
                "%s.AccountActivateView.get() invalid password reset link. User does not exist.",
                self.formatted_class_name,
            )
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
            logger.error(
                "%s.AccountActivateView.get() bad token error: %s\n%s",
                self.formatted_class_name,
                str(e),
                traceback.format_exc(),
            )
            return SmarterHttpResponseBadRequest(request=request, error_message=str(e))
        except SmarterTokenExpiredError as e:
            logger.debug(
                "%s.AccountActivateView.get() expired token error: %s",
                self.formatted_class_name,
                str(e),
            )
            return SmarterHttpResponseForbidden(request=request, error_message=str(e))

        return self.clean_http_response(request, template_path=self.template_path)


# ------------------------------------------------------------------------------
# Private Access Views
# ------------------------------------------------------------------------------
class AccountDeactivateView(SmarterAuthenticatedNeverCachedWebView):
    """View for the account deactivation page."""

    template_path = "account/account-deactivated.html"

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{AccountDeactivateView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)
