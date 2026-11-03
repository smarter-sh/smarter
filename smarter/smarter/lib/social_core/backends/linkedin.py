# pylint: disable=missing-module-docstring,missing-function-docstring,missing-class-docstring
"""
LinkedIn OAuth1 and OAuth2 backend, docs at:

    https://python-social-auth.readthedocs.io/en/latest/backends/linkedin.html
"""

import datetime
from calendar import timegm
from datetime import timezone

from social_core.backends.oauth import BaseOAuth2
from social_core.backends.open_id_connect import OpenIdConnectAuth
from social_core.exceptions import AuthCanceled, AuthTokenError

from smarter.lib import logging

logger = logging.getLogger(__name__)


class LinkedinOpenIdConnect(OpenIdConnectAuth):
    """
    Linkedin OpenID Connect backend.

    Oauth2 has been deprecated as of August 1, 2023.
    https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/sign-in-with-linkedin-v2?context=linkedin/consumer/context
    """

    name = "linkedin-openidconnect"
    # Settings from https://www.linkedin.com/oauth/.well-known/openid-configuration
    OIDC_ENDPOINT = "https://www.linkedin.com/oauth"

    # https://developer.okta.com/docs/reference/api/oidc/#response-example-success-9
    # Override this value as it is not provided by Linkedin.
    # else our request falls back to basic auth which is not supported.
    TOKEN_ENDPOINT_AUTH_METHOD = "client_secret_post"

    def validate_claims(self, id_token):
        """Copy of the regular validate_claims method without the nonce validation."""

        utc_timestamp = timegm(datetime.datetime.now(timezone.utc).utctimetuple())

        if "nbf" in id_token and utc_timestamp < id_token["nbf"]:
            raise AuthTokenError(self, "Incorrect id_token: nbf")

        # Verify the token was issued in the last 10 minutes
        iat_leeway = self.setting("ID_TOKEN_MAX_AGE", self.ID_TOKEN_MAX_AGE)
        if utc_timestamp > id_token["iat"] + iat_leeway:
            raise AuthTokenError(self, "Incorrect id_token: iat")

        # Skip the nonce validation for linkedin as it does not provide any nonce.
        # https://stackoverflow.com/questions/76889585/issues-with-sign-in-with-linkedin-using-openid-connect


class LinkedinOAuth2(BaseOAuth2):
    """Python-social-auth backend for signing in with LinkedIn, by OAuth2 with the OpenID Connect scopes."""

    name = "linkedin-oauth2"
    AUTHORIZATION_URL = "https://www.linkedin.com/oauth/v2/authorization"
    ACCESS_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
    USER_DETAILS_URL = "https://api.linkedin.com/v2/userinfo?projection=({projection})"
    USER_EMAILS_URL = "https://api.linkedin.com/v2/emailAddress" "?q=members&projection=(elements*(handle~))"
    ACCESS_TOKEN_METHOD = "POST"
    REDIRECT_STATE = False
    DEFAULT_SCOPE = ["openid", "profile", "email"]
    EXTRA_DATA = [
        ("id", "id"),
        ("expires_in", "expires"),
        ("firstName", "first_name"),
        ("lastName", "last_name"),
        ("refresh_token", "refresh_token"),
        ("refresh_token_expires_in", "refresh_expires_in"),
    ]

    def user_details_url(self):
        """Return the userinfo url, projecting ``id``, ``firstName``, ``lastName`` and the ``FIELD_SELECTORS`` setting."""
        extra_field_selectors = self.setting("FIELD_SELECTORS", [])
        # a FIELD_SELECTORS setting of None means no extra fields.
        if extra_field_selectors is None:
            extra_field_selectors = []
        # use set() since LinkedIn fails when values are duplicated
        unique_field_selectors = set(["id", "firstName", "lastName"] + extra_field_selectors)
        fields_selectors = list(unique_field_selectors)
        # user sort to ease the tests URL mocking
        fields_selectors.sort()
        fields_selectors = ",".join(fields_selectors)
        return self.USER_DETAILS_URL.format(projection=fields_selectors)

    def user_emails_url(self):
        """Return the url of the user's email addresses."""
        return self.USER_EMAILS_URL

    def user_data(self, access_token, *args, **kwargs):
        """
        Fetch the user's profile from LinkedIn, adding the first email address if ``FIELD_SELECTORS`` asks for it.

        :param access_token: The OAuth2 access token.
        :param args: Passed to :meth:`email_data`.
        :param kwargs: Passed to :meth:`email_data`.
        :returns: The profile dict.
        """
        response = self.get_json(self.user_details_url(), headers=self.user_data_headers(access_token))

        field_selectors = self.setting("FIELD_SELECTORS", [])
        # a FIELD_SELECTORS setting of None means no extra fields.
        if field_selectors is None:
            field_selectors = []
        if "emailAddress" in set(field_selectors):
            emails = self.email_data(access_token, *args, **kwargs)
            if emails:
                response["emailAddress"] = emails[0]

        return response

    def email_data(self, access_token, *args, **kwargs):
        """
        Fetch the user's email addresses from LinkedIn.

        :param access_token: The OAuth2 access token.
        :param args: Unused.
        :param kwargs: Unused.
        :returns: The non-empty email addresses.
        """
        response = self.get_json(self.user_emails_url(), headers=self.user_data_headers(access_token))
        email_addresses = []
        for element in response.get("elements", []):
            email_address = element.get("handle~", {}).get("emailAddress")
            email_addresses.append(email_address)
        return list(filter(None, email_addresses))

    def get_user_details(self, response):
        """Return user details from Linkedin account."""

        def get_localized_name(name):
            """
            FirstName & Last Name object.

            {
                  'localized': {
                     'en_US': 'Smith'
                  },
                  'preferredLocale': {
                     'country': 'US',
                     'language': 'en'
                  }
            }
            :return the localizedName from the lastName object
            """
            locale = "{}_{}".format(name["preferredLocale"]["language"], name["preferredLocale"]["country"])
            return name["localized"].get(locale, "")

        response_first_name = response.get("firstName")
        response_last_name = response.get("lastName")
        if response_first_name and response_last_name:
            fullname, first_name, last_name = self.get_user_names(
                first_name=get_localized_name(response["firstName"]),
                last_name=get_localized_name(response["lastName"]),
            )
        else:
            fullname, first_name, last_name = "unknown", "unknown", "unknown"

        email = response.get("emailAddress", "unknown@mail.com")
        retval = {
            "username": first_name + last_name,
            "fullname": fullname,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
        }
        logger.info("User details: %s", retval)
        return retval

    def user_data_headers(self, access_token):
        """
        Return the headers of LinkedIn api requests: the bearer token, and ``Accept-Language`` if ``FORCE_PROFILE_LANGUAGE`` is set.

        :param access_token: The OAuth2 access token.
        :returns: The headers.
        """
        headers = {}
        lang = self.setting("FORCE_PROFILE_LANGUAGE")
        if lang:
            headers["Accept-Language"] = lang if lang is not True else self.strategy.get_language()
        headers["Authorization"] = f"Bearer {access_token}"
        return headers

    def request_access_token(self, *args, **kwargs):
        """
        Request the access token, sending the form data as query parameters, as LinkedIn expects.

        :param args: Passed to the base class.
        :param kwargs: Passed to the base class; ``data`` is moved to ``params``.
        :returns: The token response.
        """
        # LinkedIn expects a POST request with querystring parameters, despite
        # the spec http://tools.ietf.org/html/rfc6749#section-4.1.3
        kwargs["params"] = kwargs.pop("data")
        return super().request_access_token(*args, **kwargs)

    def process_error(self, data):
        """
        Raise on an OAuth2 error, or on a LinkedIn ``serviceErrorCode``.

        :param data: The response data.
        :raises AuthCanceled: If the response has a ``serviceErrorCode``.
        """
        super().process_error(data)
        if data.get("serviceErrorCode"):
            raise AuthCanceled(self, data.get("message") or data.get("status"))


class LinkedinMobileOAuth2(LinkedinOAuth2):
    """LinkedIn backend for the mobile SDK, which adds the ``x-li-src: msdk`` header."""

    name = "linkedin-mobile-oauth2"

    def user_data_headers(self, access_token):
        """
        Return the parent's headers, plus ``x-li-src: msdk``.

        :param access_token: The OAuth2 access token.
        :returns: The headers.
        """
        headers = super().user_data_headers(access_token)
        headers["x-li-src"] = "msdk"
        return headers
