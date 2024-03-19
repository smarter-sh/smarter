# -*- coding: utf-8 -*-
# pylint: disable=W0613
"""Django Authentication views."""
from http import HTTPStatus

from django import forms
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.shortcuts import HttpResponse, redirect
from django.urls import reverse

from smarter.apps.common.email_helpers import EmailHelper
from smarter.apps.common.token_generators import (
    ExpiringTokenGenerator,
    TokenConversionError,
    TokenExpiredError,
    TokenIntegrityError,
    TokenParseError,
)
from smarter.apps.common.view_helpers import (
    SmarterAuthenticatedNeverCachedWebView,
    SmarterNeverCachedWebView,
    redirect_and_expire_cache,
)


User = get_user_model()


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

    def get(self, request):
        form = LoginView.LoginForm()
        context = {"form": form}
        return self.clean_http_response(request, template_path=self.template_path, context=context)

    def post(self, request):
        form = LoginView.LoginForm(request.POST)
        authenticated_user: User = None
        if form.is_valid():
            email = form.cleaned_data["email"]
            try:
                user = User.objects.get(email=form.cleaned_data["email"])
                password = form.cleaned_data["password"]
                authenticated_user = authenticate(request, username=user.username, password=password)
                if authenticated_user is not None:
                    login(request, authenticated_user)
                    return redirect("/")
                return HttpResponse("Username and/or password do not match.", status=401)
            except User.DoesNotExist:
                return HttpResponse(f"Invalid login attempt. Unknown user {email}", status=403)
            # pylint: disable=W0718
            except Exception as e:
                return HttpResponse(f"An unknown error occurred {e.description}", status=500)
        return HttpResponse("Received invalid responses.", status=HTTPStatus.BAD_REQUEST)


class LogoutView(SmarterNeverCachedWebView):
    """View for logging out browser session."""

    def get(self, request):
        logout(request)
        return redirect("/")

    def post(self, request):
        logout(request)
        return redirect_and_expire_cache(path="/")


class AccountRegisterView(SmarterNeverCachedWebView):
    """View for signing up."""

    class SignUpForm(forms.Form):
        """Form for the sign-in page."""

        email = forms.EmailField()
        password = forms.CharField(widget=forms.PasswordInput)

    template_path = "account/authentication/sign-up.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect_and_expire_cache(path="/")

        form = AccountRegisterView.SignUpForm()
        context = {"form": form}
        return self.clean_http_response(request, template_path=self.template_path, context=context)

    def post(self, request):
        form = AccountRegisterView.SignUpForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            user = User.objects.create_user(username, password=password)
            login(request, user)
            return redirect_and_expire_cache(path="/welcome/")
        return self.get(request=request)


class AccountActivationEmailView(SmarterNeverCachedWebView):
    """View for activating an account via an email with a single-use activation link."""

    template_path = "account/activation.html"
    email_template_path = "account/authentication/email/account-activation.html"
    expiring_token = ExpiringTokenGenerator()

    def get(self, request):

        # generate and send the activation email
        user = request.user
        url = self.expiring_token.encode_link(request, user, "account_activate")
        context = {
            "account_activation": {
                "url": url,
            }
        }
        body = self.render_clean_html(request, template_path=self.email_template_path, context=context)
        subject = "Activate your account."
        to = user.email
        EmailHelper.send_email(subject=subject, body=body, to=to, html=True)

        # render a page to let the user know the email was sent. Add a link to resend the email.
        context = {"account_activation": {"resend": reverse("account_activation")}}
        return self.clean_http_response(request, template_path=self.template_path)


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
            return HttpResponse("Invalid password reset link. User does not exist.", status=404)
        except (TypeError, ValueError, OverflowError, TokenParseError, TokenConversionError, TokenIntegrityError) as e:
            return HttpResponse(e, status=HTTPStatus.BAD_REQUEST)
        except TokenExpiredError as e:
            return HttpResponse(e, status=HTTPStatus.UNAUTHORIZED)

        return self.clean_http_response(request, template_path=self.template_path)


# ------------------------------------------------------------------------------
# Private Access Views
# ------------------------------------------------------------------------------
class AccountDeactivateView(SmarterAuthenticatedNeverCachedWebView):
    """View for the account deactivation page."""

    template_path = "account/account-deactivated.html"
