"""Test :mod:`smarter.apps.provider.utils`: secrets, web page tests, and the Google credentials helpers."""

from unittest.mock import MagicMock, patch

import requests

from smarter.apps.account.tests.factories import admin_user_factory
from smarter.apps.provider import utils
from smarter.apps.secret.models import Secret

from .test_models import ProviderTestBase


class TestProviderUtils(ProviderTestBase):
    """Test the provider utils."""

    def test_initialize_secret(self):
        """Test that a secret is created, then updated, and that an error returns None."""
        name = f"test_provider_utils_secret_{self.hash_suffix}"
        self.addCleanup(Secret.objects.filter(name=name).delete)
        secret = utils.initialize_secret("first", name, "a test secret", self.user_profile)
        self.assertEqual(secret.get_secret(), "first")
        secret = utils.initialize_secret("second", name, "a test secret", self.user_profile)
        self.assertEqual(Secret.objects.get(pk=secret.pk).get_secret(), "second")
        with patch.object(Secret.objects, "update_or_create", side_effect=RuntimeError("database down")):
            self.assertIsNone(utils.initialize_secret("third", name, "a test secret", self.user_profile))

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
        """Test that the key is read from the smarter admin's secret, which is initialized when it is missing."""
        secret = MagicMock()
        secret.get_secret.return_value = "maps-key"
        with patch.object(Secret, "get_cached_object", return_value=secret):
            self.assertEqual(utils.get_google_maps_api_key(), "maps-key")
        secret.get_secret.return_value = ""
        with patch.object(Secret, "get_cached_object", return_value=secret):
            self.assertIsNone(utils.get_google_maps_api_key())
        with (
            patch.object(Secret, "get_cached_object", side_effect=Secret.DoesNotExist),
            patch.object(utils, "initialize_google_maps") as initialize,
        ):
            self.assertIsNone(utils.get_google_maps_api_key())
        initialize.assert_called_once()
        with patch.object(Secret, "get_cached_object", side_effect=RuntimeError("cache down")):
            self.assertIsNone(utils.get_google_maps_api_key())

    def test_initialize_google_maps(self):
        with patch.object(utils, "get_env", return_value="maps-key"), patch.object(utils, "initialize_secret") as init:
            utils.initialize_google_maps()
        self.assertEqual(init.call_args.kwargs["secret_string"], "maps-key")
        with patch.object(utils, "get_env", return_value=""), patch.object(utils, "initialize_secret") as init:
            utils.initialize_google_maps()
        init.assert_not_called()

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
        utils.initialize_secret('{"type": "admin"}', name, "test", self.user_profile)
        utils.initialize_secret('{"type": "other"}', name, "test", other_user_profile)
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
