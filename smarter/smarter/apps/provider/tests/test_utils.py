"""Test :mod:`smarter.apps.provider.utils`: secrets, web page tests, and the Google credentials helpers."""

from unittest.mock import MagicMock, patch

import requests

from smarter.apps.account.tests.factories import admin_user_factory
from smarter.apps.provider import utils
from smarter.apps.secret.models import Secret

from .test_models import ProviderTestBase


class TestProviderUtils(ProviderTestBase):
    """Test the provider utils."""

    def test_web_page(self):
        page = MagicMock(status_code=200, text="<!DOCTYPE html><html>Terms of Service</html>")
        with patch.object(utils.requests, "get", return_value=page):
            self.assertTrue(utils.test_web_page("https://example.com/tos", "terms of service"))
            self.assertFalse(utils.test_web_page("https://example.com/tos", "privacy policy"))
        with patch.object(utils.requests, "get", return_value=MagicMock(status_code=404, text="")):
            self.assertFalse(utils.test_web_page("https://example.com/tos", ""))
        with patch.object(utils.requests, "get", side_effect=requests.ConnectionError("down")):
            self.assertFalse(utils.test_web_page("https://example.com/tos", ""))

    def test_get_google_maps_api_key(self):
        """Test that the key is read from the smarter admin's Secret, its only source, never from the environment."""
        secret = MagicMock()
        secret.get_secret.return_value = "maps-key"
        with patch.object(Secret, "get_cached_object", return_value=secret):
            self.assertEqual(utils.get_google_maps_api_key(), "maps-key")
        for missing in ("", "SET-ME-PLEASE"):
            secret.get_secret.return_value = missing
            with patch.object(Secret, "get_cached_object", return_value=secret):
                self.assertIsNone(utils.get_google_maps_api_key())
        environment = {"SMARTER_APP_PROVIDER_GOOGLE_MAPS_API_KEY": "maps-key-from-the-environment"}
        with (
            patch.dict("os.environ", environment),
            patch.object(Secret, "get_cached_object", side_effect=Secret.DoesNotExist),
            patch.object(utils, "logger") as logger,
        ):
            self.assertIsNone(utils.get_google_maps_api_key())
        logged = str(logger.error.call_args)
        self.assertIn("google_maps_api_key", logged)
        self.assertNotIn("maps-key-from-the-environment", logged)
        with patch.object(Secret, "get_cached_object", side_effect=RuntimeError("cache down")):
            self.assertIsNone(utils.get_google_maps_api_key())

    def test_google_service_account_bearer_token_errors(self):
        """Test that a missing, empty or invalid service account returns None."""
        secret = MagicMock()
        for value in ("", "not json", '{"type": "service_account"}'):
            secret.get_secret.return_value = value
            with self.subTest(value=value), patch.object(Secret, "get_cached_object", return_value=secret):
                self.assertIsNone(utils.get_google_service_account_bearer_token())
        with patch.object(Secret, "get_cached_object", side_effect=Secret.DoesNotExist):
            self.assertIsNone(utils.get_google_service_account_bearer_token())

    def test_google_service_account_bearer_token(self):
        """Test that the bearer token of the smarter admin's service account is returned, whatever other owners have."""
        name = utils.GOOGLE_SERVICE_ACCOUNT_SECRET_NAME
        # self.user_profile stands for the smarter admin. Another account has a Secret of the same name,
        # which is not deleted with factory_account_teardown(), because it sweeps the class's own accounts.
        other_user, other_account, other_user_profile = admin_user_factory()
        self.addCleanup(lambda: (other_user_profile.delete(), other_user.delete(), other_account.delete()))
        for user_profile in (self.user_profile, other_user_profile):
            self.addCleanup(Secret.objects.filter(name=name, user_profile=user_profile).delete)
        for value, owner in (('{"type": "admin"}', self.user_profile), ('{"type": "other"}', other_user_profile)):
            Secret.objects.create(name=name, user_profile=owner, encrypted_value=Secret.encrypt(value))
        credentials = MagicMock(token="bearer-token")
        cached_objects = MagicMock(smarter_admin_user_profile=self.user_profile)
        with (
            patch.object(utils, "smarter_cached_objects", cached_objects),
            patch.object(
                utils.service_account.Credentials, "from_service_account_info", return_value=credentials
            ) as from_info,
        ):
            self.assertEqual(utils.get_google_service_account_bearer_token(), "bearer-token")
        self.assertEqual(from_info.call_args.args[0], {"type": "admin"})
