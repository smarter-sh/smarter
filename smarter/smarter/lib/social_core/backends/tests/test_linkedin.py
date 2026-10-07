"""Test :mod:`smarter.lib.social_core.backends.linkedin`.

LinkedIn is never called: get_json() is mocked.
"""

import datetime
from calendar import timegm
from unittest.mock import MagicMock, patch

from social_core.exceptions import AuthCanceled, AuthTokenError

from smarter.lib.social_core.backends.linkedin import (
    LinkedinMobileOAuth2,
    LinkedinOAuth2,
    LinkedinOpenIdConnect,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


def name(value: str) -> dict:
    return {"localized": {"en_US": value}, "preferredLocale": {"language": "en", "country": "US"}}


class LinkedinTestBase(SmarterTestBase):
    """A backend with a fake strategy, and its settings in self.settings."""

    backend_class = LinkedinOAuth2

    def setUp(self):
        super().setUp()
        self.settings: dict = {}
        self.backend = self.backend_class(strategy=MagicMock())
        patcher = patch.object(
            self.backend_class, "setting", lambda backend, key, default=None: self.settings.get(key, default)
        )
        patcher.start()
        self.addCleanup(patcher.stop)


class TestLinkedinOpenIdConnect(LinkedinTestBase):
    """Test validate_claims(), which skips the nonce validation."""

    backend_class = LinkedinOpenIdConnect

    def test_validate_claims(self):
        now = timegm(datetime.datetime.now(datetime.timezone.utc).utctimetuple())
        self.backend.validate_claims({"iat": now})
        with self.assertRaises(AuthTokenError):
            self.backend.validate_claims({"iat": now, "nbf": now + 3600})
        with self.assertRaises(AuthTokenError):
            self.backend.validate_claims({"iat": now - 3600})


class TestLinkedinOAuth2(LinkedinTestBase):
    """Test the OAuth2 backend's urls, user data, user details and errors."""

    def test_user_details_url(self):
        self.settings["FIELD_SELECTORS"] = ["emailAddress", "id"]
        self.assertEqual(
            self.backend.user_details_url(),
            LinkedinOAuth2.USER_DETAILS_URL.format(projection="emailAddress,firstName,id,lastName"),
        )
        self.assertEqual(self.backend.user_emails_url(), LinkedinOAuth2.USER_EMAILS_URL)

    def test_user_data(self):
        """Test that the user's first email address is added, when the emailAddress field is selected."""
        emails = {"elements": [{"handle~": {"emailAddress": "a@example.com"}}, {"handle~": {}}, {}]}
        with patch.object(
            LinkedinOAuth2, "get_json", side_effect=lambda url, headers: {"id": "1"} if "userinfo" in url else emails
        ) as get_json:
            self.assertEqual(self.backend.user_data("token"), {"id": "1"})
            self.settings["FIELD_SELECTORS"] = ["emailAddress"]
            self.assertEqual(self.backend.user_data("token"), {"id": "1", "emailAddress": "a@example.com"})
        self.assertEqual(get_json.call_args.kwargs["headers"]["Authorization"], "Bearer token")
        with patch.object(LinkedinOAuth2, "get_json", return_value={}):
            self.assertEqual(self.backend.email_data("token"), [])

    def test_get_user_details(self):
        details = self.backend.get_user_details(
            {"firstName": name("Ada"), "lastName": name("Lovelace"), "emailAddress": "ada@example.com"}
        )
        self.assertEqual(details["first_name"], "Ada")
        self.assertEqual(details["last_name"], "Lovelace")
        self.assertEqual(details["username"], "AdaLovelace")
        self.assertEqual(details["email"], "ada@example.com")

    def test_get_user_details_without_names(self):
        details = self.backend.get_user_details({})
        self.assertEqual(details["fullname"], "unknown")
        self.assertEqual(details["email"], "unknown@mail.com")

    def test_user_data_headers(self):
        self.assertEqual(self.backend.user_data_headers("t"), {"Authorization": "Bearer t"})
        self.settings["FORCE_PROFILE_LANGUAGE"] = "fr"
        self.assertEqual(self.backend.user_data_headers("t")["Accept-Language"], "fr")
        self.settings["FORCE_PROFILE_LANGUAGE"] = True
        self.backend.strategy.get_language.return_value = "de"
        self.assertEqual(self.backend.user_data_headers("t")["Accept-Language"], "de")

    def test_request_access_token(self):
        """Test that the token request's data is sent as querystring parameters."""
        with patch(
            "social_core.backends.oauth.BaseOAuth2.request_access_token", return_value={"access_token": "t"}
        ) as request:
            self.assertEqual(self.backend.request_access_token("url", data={"code": "c"}), {"access_token": "t"})
        self.assertEqual(request.call_args.kwargs, {"params": {"code": "c"}})

    def test_process_error(self):
        self.backend.process_error({})
        with self.assertRaises(AuthCanceled):
            self.backend.process_error({"serviceErrorCode": 100, "message": "denied"})


class TestLinkedinMobileOAuth2(LinkedinTestBase):
    backend_class = LinkedinMobileOAuth2

    def test_user_data_headers(self):
        self.assertEqual(self.backend.user_data_headers("t"), {"Authorization": "Bearer t", "x-li-src": "msdk"})
