"""
Test :mod:`smarter.apps.provider.models`: Provider's status transitions, activation rules,.

api keys and connectivity test, its cached getters, and the verification models.
"""

import os
from datetime import timedelta
from unittest.mock import MagicMock, patch

import requests
from django.utils import timezone

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.provider.models import (
    Provider,
    ProviderModel,
    ProviderModelVerification,
    ProviderModelVerificationTypes,
    ProviderStatus,
    ProviderVerification,
    ProviderVerificationTypes,
)
from smarter.apps.secret.models import Secret
from smarter.common.exceptions import SmarterConfigurationError, SmarterValueError


class ProviderTestBase(TestAccountMixin):
    """Create a throwaway Provider for each test."""

    def setUp(self):
        super().setUp()
        self.provider = self.new_provider("test_provider_models")

    def new_provider(self, name: str, **kwargs) -> Provider:
        name = f"{name}_{self.hash_suffix}"
        self.addCleanup(Provider.objects.filter(name=name).delete)
        return Provider.objects.create(
            name=name, user_profile=self.user_profile, base_url="https://api.example.com/v1/", **kwargs
        )

    def accept_tos(self, provider: Provider) -> None:
        provider.tos_accepted_at = timezone.now()
        provider.tos_accepted_by = self.admin_user
        provider.save()


class TestProviderStatus(ProviderTestBase):
    """Test the Provider's activation rules and status transitions."""

    def test_can_activate(self):
        self.assertFalse(self.provider.can_activate)
        self.assertFalse(self.provider.tos_accepted)
        self.accept_tos(self.provider)
        self.assertTrue(self.provider.tos_accepted)
        self.assertFalse(self.provider.can_activate)
        self.provider.status = ProviderStatus.VERIFIED
        self.assertTrue(self.provider.can_activate)

    def test_activate(self):
        """Test that a verified provider whose terms of service are accepted can be activated, once."""
        self.accept_tos(self.provider)
        self.provider.status = ProviderStatus.VERIFIED
        self.provider.activate()
        self.assertTrue(Provider.objects.get(pk=self.provider.pk).is_active)
        self.provider.activate()
        self.assertTrue(self.provider.is_active)

    def test_activate_refused(self):
        """Test each reason that a provider cannot be activated, which also deactivates an active one."""
        cases = {
            "is_deprecated": True,
            "is_suspended": True,
            "is_flagged": True,
        }
        for attribute, value in cases.items():
            with self.subTest(attribute=attribute):
                provider = self.new_provider(f"test_provider_refused_{attribute}")
                self.accept_tos(provider)
                provider.status = ProviderStatus.VERIFIED
                provider.is_active = True
                setattr(provider, attribute, value)
                with self.assertRaises(SmarterValueError):
                    provider.activate()
                self.assertFalse(provider.is_active)
        with self.assertRaises(SmarterValueError):
            self.provider.activate()  # terms of service not accepted
        self.accept_tos(self.provider)
        with self.assertRaises(SmarterValueError):
            self.provider.activate()  # not verified

    def test_suspend_deprecate_flag(self):
        """Test that suspending, deprecating and flagging deactivate the provider, and that undoing them resets it."""
        transitions = (
            ("suspend", "unsuspend", "is_suspended", ProviderStatus.SUSPENDED),
            ("deprecate", "undeprecate", "is_deprecated", ProviderStatus.DEPRECATED),
        )
        for do, undo, attribute, status in transitions:
            with self.subTest(transition=do):
                self.provider.is_active = True
                getattr(self.provider, do)()
                self.assertTrue(getattr(self.provider, attribute))
                self.assertEqual(self.provider.status, status)
                self.assertFalse(self.provider.is_active)
                getattr(self.provider, undo)()
                self.assertFalse(getattr(self.provider, attribute))
                self.assertEqual(self.provider.status, ProviderStatus.UNVERIFIED)

        self.provider.flag()
        self.assertTrue(self.provider.is_flagged)
        self.provider.unflag()
        self.assertFalse(self.provider.is_flagged)
        self.assertEqual(self.provider.status, ProviderStatus.UNVERIFIED)

    def test_unflag_activates(self):
        """Test that unflagging a provider that can be activated activates it."""
        self.accept_tos(self.provider)
        self.provider.status = ProviderStatus.VERIFIED
        self.provider.flag()
        self.provider.unflag()
        self.assertTrue(self.provider.is_active)

    def test_verify(self):
        """Test that verify() sets the status, and requests the verification task."""
        with patch("smarter.apps.provider.tasks.verify_provider.delay") as delay:
            self.provider.verify()
        self.assertEqual(Provider.objects.get(pk=self.provider.pk).status, ProviderStatus.VERIFYING)
        delay.assert_called_once_with(provider_id=self.provider.id)


class TestProviderApiKeys(ProviderTestBase):
    """Test the Provider's production api key, authorization header and connectivity test."""

    def test_production_api_key(self):
        variable = f"{self.provider.name.upper()}_API_KEY"
        with patch.dict(os.environ, {variable: "sk-test"}):
            self.assertEqual(self.provider.production_api_key(), "********")
            self.assertEqual(self.provider.production_api_key(mask=False), "sk-test")
            self.assertEqual(self.provider.authorization_header, {"Authorization": "Bearer sk-test"})
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(variable, None)
            with self.assertRaises(SmarterConfigurationError):
                self.provider.production_api_key()

    def test_authorization_header_with_api_key(self):
        """Test that the authorization header uses the provider's api key, when there is no production api key."""
        self.provider.api_key = Secret.objects.create(
            name=f"test_provider_models_key_{self.hash_suffix}",
            user_profile=self.user_profile,
            encrypted_value=Secret.encrypt("sk-secret"),
        )
        self.addCleanup(Secret.objects.filter(pk=self.provider.api_key.pk).delete)
        self.assertEqual(self.provider.authorization_header, {"Authorization": "Bearer sk-secret"})

    def test_connectivity(self):
        """Test the connectivity test, without an api key, for a 200, another status, and a network error."""
        with patch("smarter.apps.provider.models.requests.get", return_value=MagicMock(status_code=200)) as get:
            self.assertTrue(self.provider.test_connectivity())
        self.assertTrue(get.call_args.args[0].startswith("https://api.example.com/v1/"))
        with patch("smarter.apps.provider.models.requests.get", return_value=MagicMock(status_code=401)):
            self.assertFalse(self.provider.test_connectivity())
        with patch("smarter.apps.provider.models.requests.get", side_effect=requests.ConnectionError("down")):
            self.assertFalse(self.provider.test_connectivity())
        self.provider.base_url = None
        with self.assertRaises(SmarterValueError):
            self.provider.test_connectivity()


class TestProviderProperties(ProviderTestBase):
    """Test the Provider's other properties, and its cached getters."""

    def test_properties(self):
        self.assertTrue(self.provider.is_billable_resource)
        self.assertFalse(self.provider.is_official_provider)
        self.assertEqual(self.provider.rfc1034_compliant_name, self.provider.name.replace("_", "-"))
        self.assertIn(self.provider.name, str(self.provider))
        self.assertIsNone(self.provider.validate())

    def test_get_cached_provider_by_name(self):
        found = Provider.get_cached_provider_by_account_id_and_name(
            invalidate=True, account_id=self.account.id, name=self.provider.name
        )
        self.assertEqual(found, self.provider)
        self.assertIsNone(
            Provider.get_cached_provider_by_account_id_and_name(account_id=self.account.id, name="no_such_provider")
        )
        self.assertEqual(
            Provider.get_cached_provider_by_user_and_name(user=self.admin_user, name=self.provider.name), self.provider
        )

    def test_get_cached_providers_for_user(self):
        self.assertIn(self.provider, Provider.get_cached_providers_for_user(invalidate=True, user=self.admin_user))

    def test_get_cached_providers_for_user_invalidate(self):
        """Test that invalidate=True shows a new provider."""
        Provider.get_cached_providers_for_user(user=self.admin_user)
        provider = self.new_provider("test_provider_models_newer")
        self.assertIn(provider, Provider.get_cached_providers_for_user(invalidate=True, user=self.admin_user))


class TestVerificationModels(ProviderTestBase):
    """Test ProviderVerification and ProviderModelVerification."""

    def test_provider_verification_is_valid(self):
        verification = ProviderVerification.objects.create(
            provider=self.provider, verification_type=ProviderVerificationTypes.LOGO, is_successful=True
        )
        ProviderVerification.objects.filter(pk=verification.pk).update(updated_at=timezone.now() - timedelta(hours=1))
        verification.refresh_from_db()
        self.assertTrue(verification.is_valid)
        self.assertIn("Success", str(verification))
        ProviderVerification.objects.filter(pk=verification.pk).update(updated_at=timezone.now() - timedelta(days=30))
        verification.refresh_from_db()
        self.assertFalse(verification.is_valid)

    def test_next_verification(self):
        """Test that next_verification is a datetime."""
        verification = ProviderVerification.objects.create(
            provider=self.provider, verification_type=ProviderVerificationTypes.LOGO, is_successful=True
        )
        self.assertGreater(verification.next_verification, verification.updated_at)

    def test_provider_model_verification(self):
        model = ProviderModel.objects.create(provider=self.provider, name="test-model")
        self.assertIn("test-model", str(model))
        verification = ProviderModelVerification.objects.create(
            provider_model=model, verification_type=ProviderModelVerificationTypes.TOOLS, is_successful=False
        )
        self.assertFalse(verification.is_valid)
        self.assertIn("test-model", str(verification))
