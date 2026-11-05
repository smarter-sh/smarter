"""
LinkedIn OpenID Connect and OAuth2 backends for python-social-auth.

They adapt the backends that python-social-auth documents at
https://python-social-auth.readthedocs.io/en/latest/backends/linkedin.html to LinkedIn's
current api.
"""

import datetime
from calendar import timegm
from datetime import timezone

from social_core.backends.oauth import BaseOAuth2
from social_core.backends.open_id_connect import OpenIdConnectAuth
from social_core.exceptions import AuthCanceled, AuthTokenError

from smarter.lib import logging

logger = logging.getLogger(__name__)
logger_prefix = logging.SmarterFormattedText.text(__name__)


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

    def validate_claims(self, id_token: dict) -> None:
        """
        Validate the id token's claims, like the base class, but without the nonce validation.

        LinkedIn does not provide a nonce, so only the ``nbf`` (not before) and ``iat`` (issued
        at) claims are checked.

        :param id_token: The decoded id token.
        :raises AuthTokenError: If the token is not valid yet, or was issued more than
            ``ID_TOKEN_MAX_AGE`` seconds ago.
        """
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
    USER_EMAILS_URL = "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))"
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

    def _field_selectors(self) -> list:
        """
        Return the ``FIELD_SELECTORS`` setting: the extra profile fields to request.

        :returns: The field selectors, or an empty list if the setting is missing or None.
        """
        field_selectors = self.setting("FIELD_SELECTORS", [])
        # a FIELD_SELECTORS setting of None means no extra fields.
        if field_selectors is None:
            field_selectors = []
        return field_selectors

    def user_details_url(self) -> str:
        """
        Return the userinfo url, projecting ``id``, ``firstName``, ``lastName`` and the ``FIELD_SELECTORS`` setting.

        :returns: The url.
        """
        extra_field_selectors = self._field_selectors()
        # use set() since LinkedIn fails when values are duplicated
        unique_field_selectors = set(["id", "firstName", "lastName"] + extra_field_selectors)
        fields_selectors = list(unique_field_selectors)
        # user sort to ease the tests URL mocking
        fields_selectors.sort()
        fields_selectors = ",".join(fields_selectors)
        url = self.USER_DETAILS_URL.format(projection=fields_selectors)
        return url

    def user_emails_url(self) -> str:
        """
        Return the url of the user's email addresses.

        :returns: The url.
        """
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

        field_selectors = self._field_selectors()
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
            handle = element.get("handle~", {})
            email_address = handle.get("emailAddress")
            email_addresses.append(email_address)
        non_empty_email_addresses = list(filter(None, email_addresses))
        return non_empty_email_addresses

    def get_user_details(self, response: dict) -> dict:
        """
        Return the user's details from their LinkedIn profile.

        A profile without both a first and a last name gets ``unknown`` names, and one without
        an email address gets ``unknown@mail.com``.

        :param response: The profile, from :meth:`user_data`.
        :returns: A dict of ``username``, ``fullname``, ``first_name``, ``last_name`` and
            ``email``.
        """

        def get_localized_name(name: dict) -> str:
            """
            Return a ``firstName`` or ``lastName`` object's name in its preferred locale.

            The object looks like this:

            .. code-block:: python

                {
                    "localized": {"en_US": "Smith"},
                    "preferredLocale": {"country": "US", "language": "en"},
                }

            :param name: The name object.
            :returns: The name in the preferred locale, or an empty string if it has none.
            """
            preferred_locale = name["preferredLocale"]
            language = preferred_locale["language"]
            country = preferred_locale["country"]
            locale = f"{language}_{country}"
            localized_name = name["localized"].get(locale, "")
            return localized_name

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
        # The details are personal data (name, email), so only the username is logged.
        logger.debug("%s.LinkedinOAuth2.get_user_details() username=%s", logger_prefix, retval["username"])
        return retval

    def user_data_headers(self, access_token: str) -> dict:
        """
        Return the headers of LinkedIn api requests: the bearer token, and ``Accept-Language`` if ``FORCE_PROFILE_LANGUAGE`` is set.

        A ``FORCE_PROFILE_LANGUAGE`` of True means the strategy's current language.

        :param access_token: The OAuth2 access token.
        :returns: The headers.
        """
        headers = {}
        lang = self.setting("FORCE_PROFILE_LANGUAGE")
        if lang:
            if lang is True:
                lang = self.strategy.get_language()
            headers["Accept-Language"] = lang
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

    def process_error(self, data: dict) -> None:
        """
        Raise on an OAuth2 error, or on a LinkedIn ``serviceErrorCode``.

        :param data: The response data.
        :raises AuthCanceled: If the response has a ``serviceErrorCode``.
        """
        super().process_error(data)
        if data.get("serviceErrorCode"):
            reason = data.get("message")
            if not reason:
                reason = data.get("status")
            raise AuthCanceled(self, reason)


class LinkedinMobileOAuth2(LinkedinOAuth2):
    """LinkedIn backend for the mobile SDK, which adds the ``x-li-src: msdk`` header."""

    name = "linkedin-mobile-oauth2"

    def user_data_headers(self, access_token: str) -> dict:
        """
        Return the parent's headers, plus ``x-li-src: msdk``.

        :param access_token: The OAuth2 access token.
        :returns: The headers.
        """
        headers = super().user_data_headers(access_token)
        headers["x-li-src"] = "msdk"
        return headers
